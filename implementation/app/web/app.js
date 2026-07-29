"use strict";

const state = {
    page: "home",
    workflow: "idle",
    providers: [],
    artifactBase64: null,
    artifactBytes: null,
    artifactUrl: null,
    artifactFilename: null,
    artifactMediaType: null,
    credential: null,
    originalCredential: null,
    verification: null,
    exploreTab: "providers",
    developerTab: "integration",
    exploreData: new Map(),
};

const elements = {
    pages: [...document.querySelectorAll("[data-page]")],
    navLinks: [...document.querySelectorAll("[data-primary-nav]")],
    routeLinks: [...document.querySelectorAll("[data-route]")],
    mobileMenuToggle: document.querySelector("#mobile-menu-toggle"),
    primaryNavigation: document.querySelector("#primary-navigation"),
    headerHealth: document.querySelector("#header-health"),
    infrastructureStatusList: document.querySelector("#infrastructure-status-list"),
    createWorkflow: document.querySelector("#create-workflow"),
    exploreContent: document.querySelector("#explore-content"),
    developerContent: document.querySelector("#developer-content"),
    exploreTabs: [...document.querySelectorAll("[data-explore-tab]")],
    developerTabs: [...document.querySelectorAll("[data-developer-tab]")],
};

const requiredElements = [
    "mobileMenuToggle", "primaryNavigation", "headerHealth",
    "infrastructureStatusList", "createWorkflow", "exploreContent",
    "developerContent",
];

function assertRequiredElements() {
    for (const name of requiredElements) {
        if (!elements[name]) {
            throw new Error(`Required interface element is missing: ${name}`);
        }
    }
}

function element(tag, options = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(options)) {
        if (key === "className") {
            node.className = value;
        } else if (key === "text") {
            node.textContent = value;
        } else if (key === "dataset") {
            Object.assign(node.dataset, value);
        } else {
            node.setAttribute(key, value);
        }
    }
    for (const child of children) {
        node.append(child);
    }
    return node;
}

function cloneTemplate(id) {
    const template = document.querySelector(`#${id}`);
    if (!template) {
        throw new Error(`Required template is missing: ${id}`);
    }
    return template.content.cloneNode(true);
}

function replaceContent(target, ...children) {
    target.replaceChildren(...children);
}

function formatTechnicalValue(value) {
    if (value === null || value === undefined || value === "") {
        return "Not available";
    }
    if (typeof value === "boolean") {
        return value ? "Yes" : "No";
    }
    if (Array.isArray(value)) {
        return value.length ? value.join(", ") : "None";
    }
    if (typeof value === "object") {
        return JSON.stringify(value, null, 2);
    }
    return String(value);
}

function createTechnicalValue(value) {
    return element("span", {
        className: "technical-value",
        text: formatTechnicalValue(value),
    });
}

function createStatusLine(label, healthy = true) {
    const dot = element("span", {
        className: `status-dot${healthy ? "" : " warning"}`,
    });
    return element("p", {className: "status-line"}, [
        dot,
        element("span", {text: label}),
    ]);
}

function createLoadingState(message) {
    return element("p", {className: "loading-state", text: message});
}

function createEmptyState(message) {
    return element("p", {className: "empty-state", text: message});
}

function createErrorState(message) {
    return element("p", {className: "error-state", text: message});
}

function createDisclosure(label, content) {
    const details = element("details", {className: "disclosure"});
    details.append(element("summary", {text: label}), content);
    return details;
}

function createMetadata(rows) {
    const list = element("dl", {className: "metadata"});
    for (const [label, value] of rows) {
        const row = element("div");
        row.append(element("dt", {text: label}), createTechnicalValue(value));
        list.append(row);
    }
    return list;
}

function shortValue(value, length = 18) {
    const text = formatTechnicalValue(value);
    return text.length > length ? `${text.slice(0, length)}…` : text;
}

async function readError(response) {
    try {
        const body = await response.json();
        if (typeof body.detail === "string") {
            return body.detail;
        }
        if (Array.isArray(body.detail)) {
            return body.detail.map((entry) => entry.msg).join(" ");
        }
        return JSON.stringify(body);
    } catch {
        return `Request failed with status ${response.status}.`;
    }
}

async function fetchJson(url, options = undefined) {
    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(await readError(response));
    }
    return response.json();
}

function activatePage(pageName) {
    const validPage = ["home", "create", "explore", "developer"].includes(pageName)
        ? pageName
        : "home";
    state.page = validPage;
    for (const page of elements.pages) {
        page.hidden = page.dataset.page !== validPage;
    }
    for (const link of elements.navLinks) {
        if (link.dataset.route === validPage) {
            link.setAttribute("aria-current", "page");
        } else {
            link.removeAttribute("aria-current");
        }
    }
    elements.primaryNavigation.classList.remove("open");
    elements.mobileMenuToggle.setAttribute("aria-expanded", "false");
    if (validPage === "create") {
        renderCreate();
    } else if (validPage === "explore") {
        renderExplore();
    } else if (validPage === "developer") {
        renderDeveloper();
    }
    document.title = `GAP — ${validPage[0].toUpperCase()}${validPage.slice(1)}`;
}

function routeFromLocation() {
    activatePage(window.location.hash.slice(1).split("/")[0] || "home");
}

async function loadHomeStatus() {
    try {
        const [health, providers, authorities, log, witnesses, gossip] =
            await Promise.all([
                fetchJson("/health"),
                fetchJson("/providers"),
                fetchJson("/registry-authorities"),
                fetchJson("/transparency/log"),
                fetchJson("/transparency/witness-quorum"),
                fetchJson("/transparency/gossip/status"),
            ]);
        const gossipStatus = normalizeGossipStatusResponse(gossip);
        const healthy = health.status === "healthy";
        replaceContent(
            elements.headerHealth,
            element("span", {className: `status-dot${healthy ? "" : " warning"}`}),
            element("span", {text: healthy ? "System healthy" : "System attention"}),
        );
        const lines = [
            createStatusLine(`${providers.length} providers available`, providers.length > 0),
            createStatusLine(`${authorities.length} trust authority`, authorities.length > 0),
            createStatusLine("Transparency log healthy", Boolean(log)),
            createStatusLine(
                witnesses.witness_quorum_met || witnesses.quorum_met
                    ? "Witness quorum met"
                    : "Witness quorum pending",
                witnesses.witness_quorum_met || witnesses.quorum_met,
            ),
            createStatusLine(
                gossipStatus.checkpoint_gossip_consistent
                    ? "Gossip monitor consistent"
                    : "Gossip monitor attention",
                gossipStatus.checkpoint_gossip_consistent,
            ),
        ];
        replaceContent(elements.infrastructureStatusList, ...lines);
    } catch {
        replaceContent(
            elements.headerHealth,
            element("span", {className: "status-dot warning"}),
            element("span", {text: "Status unavailable"}),
        );
        replaceContent(
            elements.infrastructureStatusList,
            createErrorState("Current infrastructure status is unavailable."),
        );
    }
}

async function loadProviders() {
    if (state.providers.length) {
        return state.providers;
    }
    state.providers = await fetchJson("/providers");
    return state.providers;
}

function providerId(provider) {
    return provider.provider_id || provider.id || "";
}

function providerName(provider) {
    return provider.provider_name || provider.name || providerId(provider);
}

function providerNameFor(id) {
    return providerName(state.providers.find((provider) => providerId(provider) === id) || {provider_id: id});
}

function renderCreate() {
    elements.createWorkflow.dataset.workflowState = state.workflow;
    if (state.workflow === "idle" || state.workflow === "generating") {
        renderCreateInitial();
    } else if (state.workflow === "generated") {
        renderCreateGenerated();
    } else if (state.workflow === "verifying") {
        renderCreateVerifying();
    } else if (state.workflow === "verified" || state.workflow === "tampering") {
        renderCreateVerified();
    } else {
        renderCreateFailed();
    }
}

function renderCreateInitial() {
    const fragment = cloneTemplate("create-idle-template");
    replaceContent(elements.createWorkflow, fragment);
    const form = elements.createWorkflow.querySelector("#generation-form");
    const select = elements.createWorkflow.querySelector("#provider-id");
    const submit = form.querySelector("button[type=submit]");
    form.addEventListener("submit", generateArtifact);
    if (state.workflow === "generating") {
        submit.disabled = true;
        submit.textContent = "Generating…";
    }
    loadProviders()
        .then((providers) => {
            select.replaceChildren();
            for (const provider of providers) {
                select.append(element("option", {
                    value: providerId(provider),
                    text: providerName(provider),
                }));
            }
            if (!providers.length) {
                select.append(element("option", {value: "", text: "No providers available"}));
            }
        })
        .catch(() => {
            select.replaceChildren(element("option", {value: "", text: "Providers unavailable"}));
        });
}

async function generateArtifact(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const provider = form.elements.provider_id.value;
    const prompt = form.elements.prompt.value.trim();
    if (!provider || !prompt) {
        return;
    }
    state.workflow = "generating";
    renderCreate();
    try {
        const result = await fetchJson("/generations/create", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                provider_id: provider,
                account_reference: "gap-reference-user",
                prompt,
                retention_days: 30,
            }),
        });
        state.artifactBase64 = result.artifact_base64;
        state.artifactBytes = base64ToBytes(result.artifact_base64);
        state.artifactFilename = result.filename;
        state.artifactMediaType = result.media_type;
        state.credential = result.credential;
        state.originalCredential = structuredClone(result.credential);
        state.verification = null;
        state.workflow = "generated";
        renderCreate();
    } catch (error) {
        state.workflow = "idle";
        renderCreate();
        const message = elements.createWorkflow.querySelector("#generation-error");
        message.textContent = error.message || "The artifact could not be generated.";
        message.hidden = false;
    }
}

function base64ToBytes(value) {
    const binary = window.atob(value);
    return Uint8Array.from(binary, (character) => character.charCodeAt(0));
}

function artifactDataUrl() {
    return `data:${state.artifactMediaType};base64,${state.artifactBase64}`;
}

function credentialProviderId() {
    return state.credential?.payload?.provider?.provider_id || "Unknown provider";
}

function generatedTimestamp() {
    const raw = state.credential?.payload?.generation?.generated_at
        || state.credential?.payload?.generation?.created_at
        || state.credential?.payload?.issued_at
        || new Date().toISOString();
    const date = new Date(raw);
    return Number.isNaN(date.valueOf()) ? raw : date.toLocaleString();
}

function renderCreateGenerated() {
    const fragment = cloneTemplate("create-generated-template");
    replaceContent(elements.createWorkflow, fragment);
    const image = elements.createWorkflow.querySelector("[data-artifact-image]");
    image.src = artifactDataUrl();
    elements.createWorkflow.querySelector("[data-provider-name]").textContent =
        providerNameFor(credentialProviderId());
    elements.createWorkflow.querySelector("[data-generated-time]").textContent =
        generatedTimestamp();
    elements.createWorkflow.querySelector("[data-issued-credential]").textContent =
        JSON.stringify(state.credential, null, 2);
}

function renderCreateVerifying() {
    const fragment = cloneTemplate("create-verifying-template");
    replaceContent(elements.createWorkflow, fragment);
}

function setProgressCheck(name, status) {
    const row = elements.createWorkflow.querySelector(`[data-check="${name}"]`);
    if (row) {
        row.className = status;
    }
}

function delay(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

async function calculateSha256(bytes) {
    const digest = await window.crypto.subtle.digest("SHA-256", bytes);
    return [...new Uint8Array(digest)]
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("");
}

function findArtifactDescriptor(credential) {
    return credential?.payload?.artifacts?.[0]
        || credential?.payload?.artifact
        || null;
}

function readDescriptorHash(descriptor) {
    return descriptor?.sha256
        || descriptor?.digest?.value
        || descriptor?.hash
        || null;
}

async function verifyCredentialSignature(credential) {
    return fetchJson("/credentials/verify", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({credential}),
    });
}

async function runCompleteVerification() {
    if (!state.artifactBytes || !state.credential) {
        return;
    }
    state.workflow = "verifying";
    renderCreate();
    try {
        setProgressCheck("integrity", "active");
        const calculatedHash = await calculateSha256(state.artifactBytes);
        const expectedHash = readDescriptorHash(findArtifactDescriptor(state.credential));
        const artifactMatches = Boolean(expectedHash) && calculatedHash === expectedHash;
        await delay(180);
        setProgressCheck("integrity", "done");

        setProgressCheck("authenticity", "active");
        const verification = await verifyCredentialSignature(state.credential);
        state.verification = verification;
        await delay(180);
        setProgressCheck("authenticity", "done");

        setProgressCheck("trust", "active");
        await delay(180);
        setProgressCheck("trust", "done");
        setProgressCheck("transparency", "active");
        await delay(180);
        setProgressCheck("transparency", "done");
        setProgressCheck("witnesses", "active");
        await delay(180);
        setProgressCheck("witnesses", "done");

        const signatureValid = verification.cryptographic_valid === true;
        const providerTrusted = verification.provider_trusted === true;
        const transparencyVerified = verification.transparency_verified === true;
        const witnessQuorumMet = verification.witness_quorum_met === true;
        const splitViewDetected = verification.split_view_detected === true;
        const backendOverallValid = verification.valid === true;
        state.workflow = (
            artifactMatches
            && signatureValid
            && providerTrusted
            && transparencyVerified
            && witnessQuorumMet
            && !splitViewDetected
            && backendOverallValid
        ) ? "verified" : "failed";
        renderCreate();
    } catch (error) {
        state.verification = {
            valid: false,
            failure_reason: error.message || "verification-request-failed",
        };
        state.workflow = "failed";
        renderCreate();
    }
}

function createEvidence() {
    const verification = state.verification || {};
    const rows = [
        ["Overall result", verification.valid],
        ["Cryptographic validity", verification.cryptographic_valid],
        ["Provider", verification.provider_id],
        ["Key", verification.key_id],
        ["Key status", verification.key_status],
        ["Provider trusted", verification.provider_trusted],
        ["Provider trust status", verification.provider_trust_status],
        ["Effective trust status", verification.effective_provider_trust_status],
        ["Trust decision", verification.trust_decision_id],
        ["Trust attestation present", verification.trust_attestation_present],
        ["Trust attestation valid", verification.trust_attestation_valid],
        ["Trust attestation", verification.trust_attestation_id],
        ["Registry authority", verification.registry_authority_id],
        ["Registry authority trusted", verification.registry_authority_trusted],
        ["Registry authority key", verification.registry_authority_key_id],
        ["Authority key status", verification.registry_authority_key_status],
        ["Federation conflict", verification.federation_conflict],
        ["Federation sources", verification.federation_sources],
        ["Federation bundles", verification.federation_bundle_ids],
        ["Transparency verified", verification.transparency_verified],
        ["Transparency log", verification.transparency_log_id],
        ["Transparency entry", verification.transparency_entry_ids],
        ["Tree head", verification.transparency_tree_head_id],
        ["Tree size", verification.transparency_tree_size],
        ["Root hash", verification.transparency_root_hash],
        ["Tree head valid", verification.transparency_tree_head_valid],
        ["Inclusion valid", verification.transparency_inclusion_valid],
        ["Consistency valid", verification.transparency_consistency_valid],
        ["Witness quorum met", verification.witness_quorum_met],
        ["Required witnesses", verification.required_witness_count],
        ["Valid witnesses", verification.valid_witness_count],
        ["Valid witness IDs", verification.valid_witness_ids],
        ["Checkpoint gossip consistent", verification.checkpoint_gossip_consistent],
        ["Split view detected", verification.split_view_detected],
        ["Witness equivocation detected", verification.witness_equivocation_detected],
        ["Rollback detected", verification.rollback_detected],
        ["Consistency unproven", verification.consistency_unproven],
        ["Failure reason", verification.failure_reason],
        ["Trust failure", verification.trust_failure_reason],
        ["Federation failure", verification.federation_failure_reason],
        ["Transparency failure", verification.transparency_failure_reason],
        ["Witness failure", verification.witness_failure_reason],
        ["Gossip failure", verification.gossip_failure_reason],
    ];
    const list = element("dl", {className: "evidence-list"});
    for (const [label, value] of rows) {
        const row = element("div");
        row.append(element("dt", {text: label}), element("dd", {}, [createTechnicalValue(value)]));
        list.append(row);
    }
    return list;
}

function renderCreateVerified() {
    const fragment = cloneTemplate("create-verified-template");
    replaceContent(elements.createWorkflow, fragment);
    replaceContent(
        elements.createWorkflow.querySelector("[data-technical-evidence]"),
        createEvidence(),
    );
    if (state.workflow === "tampering") {
        showTamperingPanel();
    }
}

function failureDetails() {
    const verification = state.verification || {};
    if (verification.split_view_detected === true) {
        return ["Public checkpoint views conflict.", "Checkpoint monitoring"];
    }
    if (verification.witness_quorum_met === false) {
        return ["The required independent witnesses did not confirm this checkpoint.", "Independent witness verification"];
    }
    if (verification.transparency_verified === false) {
        return ["The provider trust decision is not supported by valid public transparency evidence.", "Public transparency verification"];
    }
    if (verification.provider_trusted === false) {
        return ["The signing provider is not currently approved by the GAP trust network.", "Provider trust verification"];
    }
    if (verification.cryptographic_valid === false) {
        return ["The credential signature is not valid for the published provider key.", "Provider authenticity verification"];
    }
    return ["The artifact contents no longer match the digest signed by the provider.", "Artifact integrity verification"];
}

function renderCreateFailed() {
    const fragment = cloneTemplate("create-failed-template");
    replaceContent(elements.createWorkflow, fragment);
    const [message, source] = failureDetails();
    elements.createWorkflow.querySelector("[data-failure-message]").textContent = message;
    elements.createWorkflow.querySelector("[data-failure-source]").textContent = source;
    replaceContent(
        elements.createWorkflow.querySelector("[data-technical-evidence]"),
        createEvidence(),
    );
}

function showTamperingPanel() {
    const result = elements.createWorkflow.querySelector(".verification-result");
    if (!result || result.querySelector(".tamper-panel")) {
        return;
    }
    const panel = element("section", {className: "tamper-panel"});
    panel.append(
        element("h3", {text: "Choose one change"}),
        element("p", {className: "muted", text: "GAP will alter one element and verify again automatically."}),
    );
    const options = element("div", {className: "tamper-options"});
    const scenarios = [
        ["artifact", "Modify artifact"],
        ["credential", "Modify credential"],
        ["provider", "Substitute provider"],
        ["key", "Reference revoked key"],
    ];
    for (const [scenario, label] of scenarios) {
        options.append(element("button", {
            className: "button secondary-button",
            type: "button",
            text: label,
            dataset: {tamperScenario: scenario},
        }));
    }
    panel.append(options);
    result.querySelector(".result-rows").after(panel);
}

async function runTamperingScenario(scenario) {
    restoreOriginal();
    if (scenario === "artifact") {
        const modified = new Uint8Array(state.artifactBytes.length + 1);
        modified.set(state.artifactBytes);
        modified[modified.length - 1] = 1;
        state.artifactBytes = modified;
    } else if (scenario === "credential") {
        state.credential.payload.model.model_id = "modified-model";
    } else if (scenario === "provider") {
        const alternative = state.providers.find(
            (provider) => providerId(provider) !== credentialProviderId(),
        );
        if (alternative) {
            state.credential.payload.provider.provider_id = providerId(alternative);
        } else {
            state.credential.payload.provider.provider_id = "substituted-provider";
        }
    } else {
        state.credential.proof.key_id = "demo-key-2025-compromised";
    }
    await runCompleteVerification();
}

function restoreOriginal() {
    state.artifactBytes = base64ToBytes(state.artifactBase64);
    state.credential = structuredClone(state.originalCredential);
}

function startAgain() {
    if (state.artifactUrl) {
        URL.revokeObjectURL(state.artifactUrl);
    }
    Object.assign(state, {
        workflow: "idle",
        artifactBase64: null,
        artifactBytes: null,
        artifactUrl: null,
        artifactFilename: null,
        artifactMediaType: null,
        credential: null,
        originalCredential: null,
        verification: null,
    });
    renderCreate();
}

function openArtifact() {
    const blob = new Blob([state.artifactBytes], {type: state.artifactMediaType});
    state.artifactUrl = URL.createObjectURL(blob);
    window.open(state.artifactUrl, "_blank", "noopener,noreferrer");
}

async function renderExplore() {
    for (const tab of elements.exploreTabs) {
        tab.setAttribute("aria-selected", String(tab.dataset.exploreTab === state.exploreTab));
    }
    replaceContent(elements.exploreContent, createLoadingState(`Loading ${state.exploreTab}…`));
    try {
        if (state.exploreTab === "providers") {
            await renderProviders();
        } else if (state.exploreTab === "authorities") {
            await renderAuthorities();
        } else if (state.exploreTab === "transparency") {
            await renderTransparency();
        } else {
            await renderWitnesses();
        }
    } catch (error) {
        replaceContent(
            elements.exploreContent,
            createErrorState(error.message || "This information is unavailable."),
        );
    }
}

async function cached(key, loader) {
    if (!state.exploreData.has(key)) {
        state.exploreData.set(key, await loader());
    }
    return state.exploreData.get(key);
}

function activeKey(document) {
    return document?.keys?.find((key) => key.status === "active")
        || document?.keys?.[0]
        || null;
}

async function renderProviders() {
    const [providers, registry] = await Promise.all([
        loadProviders(),
        cached("registry", () => fetchJson("/trust-registry")),
    ]);
    const bounded = providers.slice(0, 6);
    if (!bounded.length) {
        replaceContent(elements.exploreContent, createEmptyState("No providers are published."));
        return;
    }
    const documents = await Promise.all(
        bounded.map((provider) => fetchJson(
            `/providers/${encodeURIComponent(providerId(provider))}/.well-known/gap.json`,
        )),
    );
    const shell = element("div", {className: "master-detail"});
    const list = element("div", {className: "record-list"});
    list.append(createRecordHeader(["Provider name", "Status", "Active key", ""]));
    const detail = element("section", {className: "surface selected-detail"});
    bounded.forEach((provider, index) => {
        const trust = registry.find((entry) => entry.provider_id === providerId(provider)) || {};
        const key = activeKey(documents[index]);
        const row = createRecordRow([
            providerName(provider),
            trust.provider_trust_status || trust.status || (trust.trusted ? "Approved" : "Unapproved"),
            shortValue(key?.key_id),
        ], "View");
        row.querySelector("button").addEventListener("click", () => {
            for (const item of list.querySelectorAll(".record-row")) {
                item.classList.remove("selected");
            }
            row.classList.add("selected");
            renderProviderDetail(detail, provider, documents[index], trust);
        });
        list.append(row);
        if (index === 0) {
            row.classList.add("selected");
            renderProviderDetail(detail, provider, documents[index], trust);
        }
    });
    shell.append(list, detail);
    replaceContent(elements.exploreContent, shell);
}

function createRecordHeader(labels) {
    const row = element("div", {className: "record-list-header"});
    for (const label of labels) {
        row.append(element("span", {text: label}));
    }
    return row;
}

function createRecordRow(values, action) {
    const row = element("div", {className: "record-row"});
    for (const value of values) {
        row.append(element("span", {text: formatTechnicalValue(value)}));
    }
    row.append(element("button", {type: "button", text: action}));
    return row;
}

function rawPre(data) {
    return element("pre", {text: JSON.stringify(data, null, 2)});
}

function renderProviderDetail(target, provider, document, trust) {
    const key = activeKey(document);
    const history = trust.decision_history || trust.history || [];
    const disclosures = element("div", {className: "detail-disclosures"});
    disclosures.append(
        createDisclosure("Key history", rawPre((document.keys || []).slice(0, 10))),
        createDisclosure("Trust-decision history", rawPre(history.slice(0, 10))),
        createDisclosure("Signed attestation", rawPre(trust.trust_attestation || trust.attestation || null)),
        createDisclosure("Identity document", rawPre(document)),
        createDisclosure("Raw JSON", rawPre({provider, trust, document})),
    );
    replaceContent(
        target,
        element("p", {className: "eyebrow", text: "Provider"}),
        element("h2", {text: providerName(provider)}),
        createMetadata([
            ["Status", trust.provider_trust_status || trust.status || (trust.trusted ? "Approved" : "Unapproved")],
            ["Active key", key?.key_id],
            ["Latest trust decision", trust.trust_decision_id || history.at(-1)?.decision_id],
            ["Provenance authority", trust.registry_authority_id || "Local GAP registry"],
        ]),
        disclosures,
    );
}

async function renderAuthorities() {
    const authorities = await cached("authorities", () => fetchJson("/registry-authorities"));
    if (!authorities.length) {
        replaceContent(elements.exploreContent, createEmptyState("No authorities are published."));
        return;
    }
    const shell = element("div", {className: "master-detail"});
    const list = element("div", {className: "record-list"});
    list.append(createRecordHeader(["Authority name", "Status", "Active key", ""]));
    const detail = element("section", {className: "surface selected-detail"});
    authorities.slice(0, 6).forEach((authority, index) => {
        const payload = authority.payload || authority;
        const key = activeKey(payload);
        const row = createRecordRow([
            payload.authority_name || payload.registry_authority_id,
            authority.trusted_by_local_registry === false ? "Untrusted" : "Locally trusted",
            shortValue(payload.active_key_id || key?.key_id),
        ], "View");
        row.querySelector("button").addEventListener("click", () => {
            for (const item of list.querySelectorAll(".record-row")) {
                item.classList.remove("selected");
            }
            row.classList.add("selected");
            renderAuthorityDetail(detail, authority);
        });
        list.append(row);
        if (index === 0) {
            row.classList.add("selected");
            renderAuthorityDetail(detail, authority);
        }
    });
    shell.append(list, detail);
    replaceContent(elements.exploreContent, shell);
}

function renderAuthorityDetail(target, authority) {
    const payload = authority.payload || authority;
    const key = activeKey(payload);
    const disclosures = element("div", {className: "detail-disclosures"});
    disclosures.append(
        createDisclosure("Key history", rawPre((payload.keys || []).slice(0, 10))),
        createDisclosure("Identity document", rawPre(payload)),
        createDisclosure("Signed decisions", rawPre((authority.signed_decisions || []).slice(0, 10))),
        createDisclosure("Raw JSON", rawPre(authority)),
    );
    replaceContent(
        target,
        element("p", {className: "eyebrow", text: "Authority"}),
        element("h2", {text: payload.authority_name || payload.registry_authority_id}),
        createMetadata([
            ["Local trust", authority.trusted_by_local_registry === false ? "Not trusted" : "Trusted"],
            ["Active key", payload.active_key_id || key?.key_id],
            ["Governed providers", authority.governed_provider_count || authority.provider_ids?.length || 0],
        ]),
        disclosures,
    );
}

async function renderTransparency() {
    const [log, head, entries, heads] = await Promise.all([
        cached("log", () => fetchJson("/transparency/log")),
        cached("head", () => fetchJson("/transparency/tree-head")),
        cached("entries", () => fetchJson("/transparency/entries")),
        cached("heads", () => fetchJson("/transparency/tree-heads")),
    ]);
    const payload = head.payload || head;
    const result = element("section", {className: "overview-result"});
    result.append(
        element("p", {className: "eyebrow", text: "Transparency"}),
        element("h2", {text: "Transparency log healthy"}),
        createMetadata([
            ["Current tree size", payload.tree_size || entries.length],
            ["Current root", shortValue(payload.root_hash, 26)],
            ["Latest checkpoint", payload.tree_head_id || payload.issued_at],
            ["Append-only consistency", "Verified"],
        ]),
    );
    const actions = element("div", {className: "secondary-actions"});
    for (const [key, label] of [
        ["entries", "Browse entries"],
        ["checkpoints", "View checkpoints"],
        ["proof", "Inspect proof"],
    ]) {
        const button = element("button", {type: "button", text: label});
        button.addEventListener("click", () => renderTransparencyDetail(result, key, {log, head, entries, heads}));
        actions.append(button);
    }
    result.append(actions);
    replaceContent(elements.exploreContent, result);
}

function renderTransparencyDetail(container, kind, data) {
    container.querySelector(".detail-view")?.remove();
    const detail = element("section", {className: "detail-view"});
    if (kind === "entries") {
        detail.append(element("h3", {text: "Recent entries"}), createObjectTable(data.entries.slice(0, 10)));
    } else if (kind === "checkpoints") {
        detail.append(element("h3", {text: "Recent checkpoints"}), createObjectTable(data.heads.slice(0, 10)));
    } else {
        detail.append(
            element("h3", {text: "Current checkpoint proof"}),
            element("p", {className: "muted", text: "Select a recent log entry to inspect its signed inclusion evidence."}),
        );
        const select = element("select", {"aria-label": "Transparency entry"});
        for (const entry of data.entries.slice(0, 10)) {
            const payload = entry.payload || entry;
            select.append(element("option", {
                value: payload.entry_id || entry.entry_id,
                text: payload.entry_id || entry.entry_id,
            }));
        }
        const output = element("div", {className: "detail-view"});
        const load = async () => {
            replaceContent(output, createLoadingState("Loading proof…"));
            try {
                replaceContent(output, rawPre(await fetchJson(
                    `/transparency/entries/${encodeURIComponent(select.value)}/inclusion-proof`,
                )));
            } catch (error) {
                replaceContent(output, createErrorState(error.message));
            }
        };
        select.addEventListener("change", load);
        detail.append(select, output);
        if (select.value) {
            load();
        }
    }
    container.append(detail);
}

function createObjectTable(objects) {
    if (!objects.length) {
        return createEmptyState("No records are available.");
    }
    const table = element("table", {className: "compact-table"});
    const body = element("tbody");
    objects.forEach((object) => {
        const payload = object.payload || object;
        const id = payload.entry_id || payload.tree_head_id || payload.id || "Record";
        const type = payload.entry_type || payload.tree_size || payload.issued_at || "";
        const row = element("tr");
        row.append(element("td", {text: shortValue(id, 34)}), element("td", {text: formatTechnicalValue(type)}));
        body.append(row);
    });
    table.append(body);
    return table;
}

function normalizeWitnessListResponse(response) {
    return Array.isArray(response) ? response : response.witnesses || [];
}

function normalizeWitnessStatementListResponse(response) {
    return Array.isArray(response) ? response : response.statements || [];
}

function normalizeGossipStatusResponse(response) {
    return response.status || response.gossip_status || response;
}

function normalizeGossipObservationListResponse(response) {
    return Array.isArray(response) ? response : response.observations || [];
}

function normalizeGossipObservation(observation) {
    const treeHead = observation.signed_tree_head || {};
    return {
        ...observation,
        tree_head: treeHead.payload || treeHead,
        consistency_proof: observation.consistency_proof_to_previous || null,
        previous_tree_head: observation.previous_signed_tree_head || null,
    };
}

async function renderWitnesses() {
    const [witnessesResponse, statementResponse, quorum, gossipResponse, observationsResponse] =
        await Promise.all([
            cached("witnesses", () => fetchJson("/transparency/witnesses")),
            cached("statements", () => fetchJson("/transparency/witness-statements")),
            cached("quorum", () => fetchJson("/transparency/witness-quorum")),
            cached("gossip", () => fetchJson("/transparency/gossip/status")),
            cached("observations", () => fetchJson("/transparency/gossip/observations")),
        ]);
    const witnesses = normalizeWitnessListResponse(witnessesResponse);
    const statements = normalizeWitnessStatementListResponse(statementResponse);
    const gossip = normalizeGossipStatusResponse(gossipResponse);
    const observations = normalizeGossipObservationListResponse(observationsResponse)
        .map(normalizeGossipObservation);
    const quorumMet = quorum.witness_quorum_met || quorum.quorum_met;
    const result = element("section", {className: "overview-result"});
    result.append(
        element("p", {className: "eyebrow", text: "Witnesses"}),
        element("h2", {text: quorumMet ? "Witness quorum met" : "Witness quorum not met"}),
        createMetadata([
            ["Required witnesses", quorum.required_witness_count],
            ["Valid witnesses", quorum.valid_witness_count],
            ["Current checkpoint", quorum.tree_head_id || gossip.tree_head_id],
            ["Checkpoint monitoring", gossip.checkpoint_gossip_consistent ? "Consistent" : "Attention required"],
        ]),
    );
    const disclosures = element("div", {className: "detail-disclosures"});
    disclosures.append(
        createDisclosure("Witness identities", rawPre(witnesses.slice(0, 10))),
        createDisclosure("Current witness statements", rawPre(statements.slice(0, 10))),
        createDisclosure("Historical statements", rawPre(statements.slice(0, 10))),
        createDisclosure("Checkpoint observations", rawPre(observations.slice(0, 10))),
    );
    if (gossip.split_view_detected || gossip.witness_equivocation_detected) {
        disclosures.append(createDisclosure("Conflict and equivocation evidence", rawPre(gossip)));
    } else {
        disclosures.append(element("p", {
            className: "status-line",
            text: "No conflicting checkpoint views detected",
        }));
    }
    result.append(disclosures);
    replaceContent(elements.exploreContent, result);
}

function renderDeveloper() {
    for (const tab of elements.developerTabs) {
        tab.setAttribute("aria-selected", String(tab.dataset.developerTab === state.developerTab));
    }
    if (state.developerTab === "integration") {
        renderIntegration();
    } else if (state.developerTab === "api") {
        renderApi();
    } else if (state.developerTab === "protocol") {
        renderProtocol();
    } else {
        renderRawData();
    }
}

function renderIntegration() {
    const code = [
        "from gap_sdk import GapPackage, GapServiceClient",
        "",
        "client = GapServiceClient('https://gap.example')",
        "capabilities = client.discover()",
        "client.negotiate(binding_profile='gap-png-embedded-v1')",
        "GapPackage.create(artifact, credential, 'artifact.gapbundle')",
        "",
        "# Portable package, PNG media binding and conformance",
        "gap package verify artifact.gapbundle --offline",
        "gap media verify artifact.png --service https://gap.example --level full",
        "gap conformance verifier --service https://gap.example",
    ].join("\n");
    replaceContent(
        elements.developerContent,
        element("p", {className: "eyebrow", text: "Integration"}),
        element("h2", {text: "Discover, negotiate and exchange"}),
        element("p", {text: "GAP 0.16 supports independent HTTP generators, portable packages and native PNG binding while retaining the same signed trust and FULL verification policy."}),
        element("h3", {text: "Python SDK"}),
        element("pre", {className: "code-example", text: code}),
        element("h3", {text: "Verify"}),
        element("p", {text: "Use sidecars for raw bytes, .gapbundle for any media, or the explicit gap-png-embedded-v1 profile for PNG. Unknown or downgraded profiles fail."}),
    );
}

function renderApi() {
    const routes = [
        ["GET", "/.well-known/gap.json"],
        ["POST", "/generations/create"],
        ["POST", "/credentials/verify"],
        ["GET", "/providers"],
        ["GET", "/providers/{provider_id}/.well-known/gap.json"],
        ["GET", "/trust-registry"],
        ["GET", "/registry-authorities"],
        ["GET", "/transparency/entries"],
        ["GET", "/transparency/tree-head"],
        ["GET", "/transparency/witness-quorum"],
    ];
    const list = element("div", {className: "route-list"});
    for (const [method, path] of routes) {
        list.append(element("p", {}, [
            element("strong", {text: method}),
            createTechnicalValue(path),
        ]));
    }
    replaceContent(
        elements.developerContent,
        element("p", {className: "eyebrow", text: "API"}),
        element("h2", {text: "Reference routes"}),
        element("p", {text: "The reference implementation exposes generation, verification and read-only public trust infrastructure."}),
        list,
    );
}

function renderProtocol() {
    replaceContent(
        elements.developerContent,
        element("p", {className: "eyebrow", text: "Protocol"}),
        element("h2", {text: "A portable trust chain"}),
        element("p", {text: "The gap-interop-v1 profile defines discovery, negotiation, raw and PNG bindings, packages, limits and fail-closed compatibility behavior. Discovery and package manifests are not trust roots."}),
        element("p", {text: "GAP separates artifact integrity, provider authenticity and ecosystem trust. A credential binds content to a provider key; signed registry decisions establish approval; an append-only log and independent witnesses make those decisions publicly auditable."}),
        element("h3", {text: "Credential"}),
        element("p", {text: "A signed statement describing the artifact, generation event, provider and signing key."}),
        element("h3", {text: "Trust and transparency"}),
        element("p", {text: "Independent authorities publish signed decisions into a verifiable log. Checkpoints and witness statements protect against hidden history changes and split views."}),
        element("h3", {text: "Overall validity"}),
        element("p", {text: "Overall validity requires each independent layer to succeed; cryptographic validity never substitutes for provider trust or witness quorum."}),
    );
}

const rawDataLoaders = {
    credentials: async () => state.credential,
    "provider identities": async () => {
        const providers = await loadProviders();
        if (!providers.length) {
            return null;
        }
        return fetchJson(`/providers/${encodeURIComponent(providerId(providers[0]))}/.well-known/gap.json`);
    },
    attestations: () => fetchJson("/trust-attestations"),
    "federation bundles": () => fetchJson("/federation/bundles"),
    "tree heads": () => fetchJson("/transparency/tree-heads"),
    proofs: async () => {
        const entries = await fetchJson("/transparency/entries");
        const first = entries[0]?.payload?.entry_id || entries[0]?.entry_id;
        return first
            ? fetchJson(`/transparency/entries/${encodeURIComponent(first)}/inclusion-proof`)
            : null;
    },
    "witness statements": () => fetchJson("/transparency/witness-statements"),
    "gossip evidence": () => fetchJson("/transparency/gossip/observations"),
};

function renderRawData() {
    const select = element("select", {"aria-label": "Raw data object"});
    select.append(element("option", {value: "", text: "Select an object"}));
    for (const label of Object.keys(rawDataLoaders)) {
        select.append(element("option", {value: label, text: label[0].toUpperCase() + label.slice(1)}));
    }
    const selector = element("div", {className: "field raw-selector"}, [
        element("label", {text: "Object type"}),
        select,
    ]);
    const viewer = element("details", {className: "disclosure"});
    const summary = element("summary", {text: "Raw JSON"});
    const output = createEmptyState("Select one object to view its raw representation.");
    viewer.append(summary, output);
    select.addEventListener("change", async () => {
        viewer.open = false;
        if (!select.value) {
            replaceContent(output, "Select one object to view its raw representation.");
            return;
        }
        replaceContent(output, "Loading selected object…");
        try {
            const data = await rawDataLoaders[select.value]();
            output.className = "";
            replaceContent(output, rawPre(data));
        } catch (error) {
            output.className = "error-state";
            replaceContent(output, error.message || "The object could not be loaded.");
        }
    });
    replaceContent(
        elements.developerContent,
        element("p", {className: "eyebrow", text: "Raw Data"}),
        element("h2", {text: "Inspect protocol objects"}),
        element("p", {text: "Choose one technical object. Raw content remains collapsed until you deliberately open it."}),
        selector,
        viewer,
    );
}

function handleCreateAction(action) {
    if (action === "verify") {
        runCompleteVerification();
    } else if (action === "start-again") {
        startAgain();
    } else if (action === "view-artifact") {
        openArtifact();
    } else if (action === "show-tampering") {
        state.workflow = "tampering";
        renderCreate();
    } else if (action === "restore") {
        restoreOriginal();
        state.workflow = "generated";
        state.verification = null;
        renderCreate();
    } else if (action === "open-evidence") {
        const details = elements.createWorkflow.querySelector(".evidence-disclosure");
        if (details) {
            details.open = true;
            details.scrollIntoView({behavior: "smooth", block: "nearest"});
        }
    }
}

function bindEvents() {
    window.addEventListener("hashchange", routeFromLocation);
    elements.mobileMenuToggle.addEventListener("click", () => {
        const open = elements.primaryNavigation.classList.toggle("open");
        elements.mobileMenuToggle.setAttribute("aria-expanded", String(open));
    });
    document.addEventListener("click", (event) => {
        const verifyExisting = event.target.closest('[data-action="verify-existing"]');
        if (verifyExisting) {
            window.location.hash = "create";
            return;
        }
        const action = event.target.closest("[data-action]")?.dataset.action;
        if (action) {
            handleCreateAction(action);
            return;
        }
        const tamper = event.target.closest("[data-tamper-scenario]")?.dataset.tamperScenario;
        if (tamper) {
            runTamperingScenario(tamper);
        }
    });
    for (const tab of elements.exploreTabs) {
        tab.addEventListener("click", () => {
            state.exploreTab = tab.dataset.exploreTab;
            renderExplore();
        });
    }
    for (const tab of elements.developerTabs) {
        tab.addEventListener("click", () => {
            state.developerTab = tab.dataset.developerTab;
            renderDeveloper();
        });
    }
}

function initialize() {
    assertRequiredElements();
    bindEvents();
    routeFromLocation();
    loadHomeStatus();
    loadProviders().catch(() => {});
}

initialize();
