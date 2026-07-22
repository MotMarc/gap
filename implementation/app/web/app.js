"use strict";


const state = {
    artifactBase64: null,
    artifactBytes: null,
    artifactFilename: null,
    artifactMediaType: null,
    credential: null,
    originalArtifactBytes: null,
    originalCredential: null,
    providers: [],
    providerDocuments: {},
    providersReady: false,
    selectedProviderDocument: null,
    providerSubstitution: null,
    revokedKeySubstitution: null,
    lastVerification: null,
};


const elements = {
    tabButtons: document.querySelectorAll("[data-tab-target]"),
    tabPages: document.querySelectorAll("[data-tab-page]"),
    generationForm: document.querySelector("#generation-form"),
    providerId: document.querySelector("#provider-id"),
    providerIdentityCard: document.querySelector("#provider-identity-card"),
    selectedProviderName: document.querySelector("#selected-provider-name"),
    selectedProviderStatus: document.querySelector(
        "#selected-provider-status"
    ),
    selectedProviderId: document.querySelector("#selected-provider-id"),
    selectedProviderGapVersion: document.querySelector(
        "#selected-provider-gap-version"
    ),
    selectedProviderKeyId: document.querySelector(
        "#selected-provider-key-id"
    ),
    selectedProviderAlgorithm: document.querySelector(
        "#selected-provider-algorithm"
    ),
    selectedProviderKeyStatus: document.querySelector(
        "#selected-provider-key-status"
    ),
    selectedProviderFingerprint: document.querySelector(
        "#selected-provider-fingerprint"
    ),
    selectedProviderKeyCount: document.querySelector(
        "#selected-provider-key-count"
    ),
    selectedProviderKeyHistory: document.querySelector(
        "#selected-provider-key-history"
    ),
    selectedProviderIdentityLink: document.querySelector(
        "#selected-provider-identity-link"
    ),
    accountReference: document.querySelector("#account-reference"),
    prompt: document.querySelector("#prompt"),
    promptCount: document.querySelector("#prompt-count"),
    retentionDays: document.querySelector("#retention-days"),
    generateButton: document.querySelector("#generate-button"),
    serviceStatus: document.querySelector("#service-status"),
    generationStatus: document.querySelector("#generation-status"),
    generationError: document.querySelector("#generation-error"),
    emptyState: document.querySelector("#empty-state"),
    resultContent: document.querySelector("#result-content"),
    artifactImage: document.querySelector("#artifact-image"),
    artifactFilename: document.querySelector("#artifact-filename"),
    artifactMediaType: document.querySelector("#artifact-media-type"),
    artifactProvider: document.querySelector("#artifact-provider"),
    artifactModel: document.querySelector("#artifact-model"),
    downloadArtifactButton: document.querySelector(
        "#download-artifact-button"
    ),
    downloadCredentialButton: document.querySelector(
        "#download-credential-button"
    ),
    openVerificationButton: document.querySelector(
        "#open-verification-button"
    ),
    artifactFileInput: document.querySelector("#artifact-file-input"),
    credentialFileInput: document.querySelector("#credential-file-input"),
    artifactUploadName: document.querySelector("#artifact-upload-name"),
    credentialUploadName: document.querySelector("#credential-upload-name"),
    useGeneratedButton: document.querySelector("#use-generated-button"),
    runVerificationButton: document.querySelector(
        "#run-verification-button"
    ),
    verificationError: document.querySelector("#verification-error"),
    completeVerificationStatus: document.querySelector(
        "#complete-verification-status"
    ),
    verificationResultIcon: document.querySelector(
        "#verification-result-icon"
    ),
    verificationResultTitle: document.querySelector(
        "#verification-result-title"
    ),
    verificationResultDescription: document.querySelector(
        "#verification-result-description"
    ),
    trustChainStatus: document.querySelector("#trust-chain-status"),
    trustCredentialNode: document.querySelector("#trust-credential-node"),
    trustIdentityNode: document.querySelector("#trust-identity-node"),
    trustKeyNode: document.querySelector("#trust-key-node"),
    trustSignatureNode: document.querySelector("#trust-signature-node"),
    trustCredentialProvider: document.querySelector(
        "#trust-credential-provider"
    ),
    trustIdentityDocument: document.querySelector(
        "#trust-identity-document"
    ),
    trustKeyId: document.querySelector("#trust-key-id"),
    trustSignatureResult: document.querySelector(
        "#trust-signature-result"
    ),
    signatureCheckIcon: document.querySelector("#signature-check-icon"),
    signatureCheckDetail: document.querySelector(
        "#signature-check-detail"
    ),
    artifactCheckIcon: document.querySelector("#artifact-check-icon"),
    artifactCheckDetail: document.querySelector("#artifact-check-detail"),
    providerCheckIcon: document.querySelector("#provider-check-icon"),
    providerCheckDetail: document.querySelector(
        "#provider-check-detail"
    ),
    timelineArtifact: document.querySelector("#timeline-artifact"),
    timelineHash: document.querySelector("#timeline-hash"),
    timelineCompare: document.querySelector("#timeline-compare"),
    timelineSignature: document.querySelector("#timeline-signature"),
    timelineProvider: document.querySelector("#timeline-provider"),
    tamperArtifactButton: document.querySelector(
        "#tamper-artifact-button"
    ),
    tamperCredentialButton: document.querySelector(
        "#tamper-credential-button"
    ),
    tamperProviderButton: document.querySelector(
        "#tamper-provider-button"
    ),
    tamperRevokedKeyButton: document.querySelector(
        "#tamper-revoked-key-button"
    ),
    restoreVerificationButton: document.querySelector(
        "#restore-verification-button"
    ),
    tamperMessage: document.querySelector("#tamper-message"),
    explorerEmpty: document.querySelector("#explorer-empty"),
    explorerContent: document.querySelector("#explorer-content"),
    explorerSignatureStatus: document.querySelector(
        "#explorer-signature-status"
    ),
    explorerVerifyButton: document.querySelector(
        "#explorer-verify-button"
    ),
    explorerCredentialId: document.querySelector(
        "#explorer-credential-id"
    ),
    explorerGenerationId: document.querySelector(
        "#explorer-generation-id"
    ),
    explorerGeneratedAt: document.querySelector(
        "#explorer-generated-at"
    ),
    explorerProviderId: document.querySelector("#explorer-provider-id"),
    explorerModelId: document.querySelector("#explorer-model-id"),
    explorerMediaType: document.querySelector("#explorer-media-type"),
    explorerArtifactHash: document.querySelector(
        "#explorer-artifact-hash"
    ),
    explorerAlgorithm: document.querySelector("#explorer-algorithm"),
    explorerKeyId: document.querySelector("#explorer-key-id"),
    credentialJson: document.querySelector("#credential-json"),
    providerEcosystemGrid: document.querySelector(
        "#provider-ecosystem-grid"
    ),
    providerEcosystemStatus: document.querySelector(
        "#provider-ecosystem-status"
    ),
    copyCredentialButton: document.querySelector(
        "#copy-credential-button"
    ),
};


function cloneValue(value) {
    return JSON.parse(JSON.stringify(value));
}


function setBadge(element, text, status) {
    element.textContent = text;
    element.classList.remove(
        "status-neutral",
        "status-success",
        "status-error"
    );
    element.classList.add(`status-${status}`);
}


function setMessage(element, text, type) {
    element.textContent = text;
    element.classList.remove(
        "hidden",
        "message-error",
        "message-success",
        "message-warning"
    );
    element.classList.add(`message-${type}`);
}


function hideMessage(element) {
    element.textContent = "";
    element.classList.add("hidden");
}


function activateTab(tabName) {
    elements.tabPages.forEach((page) => {
        page.classList.toggle(
            "hidden",
            page.dataset.tabPage !== tabName
        );
    });

    document.querySelectorAll(".navigation-button").forEach((button) => {
        button.classList.toggle(
            "active",
            button.dataset.tabTarget === tabName
        );
    });

    window.scrollTo({
        top: 0,
        behavior: "smooth",
    });
}


function setLoading(isLoading) {
    elements.generateButton.disabled = (
        isLoading ||
        !state.providersReady
    );
    elements.generateButton.classList.toggle("is-loading", isLoading);

    const label = elements.generateButton.querySelector(".button-label");

    if (!state.providersReady) {
        label.textContent = "Discovering providers";
        return;
    }

    label.textContent = isLoading
        ? "Generating artifact"
        : "Generate and issue credential";
}


function updatePromptCount() {
    elements.promptCount.textContent = (
        `${elements.prompt.value.length.toLocaleString()} / 10,000`
    );
}


function base64ToBytes(base64Value) {
    const characters = window.atob(base64Value);
    const bytes = new Uint8Array(characters.length);

    for (let index = 0; index < characters.length; index += 1) {
        bytes[index] = characters.charCodeAt(index);
    }

    return bytes;
}


function bytesToBase64(bytes) {
    let characters = "";

    bytes.forEach((value) => {
        characters += String.fromCharCode(value);
    });

    return window.btoa(characters);
}


function bytesToBlob(bytes, mediaType) {
    return new Blob([bytes], {
        type: mediaType,
    });
}


function downloadBlob(blob, filename) {
    const objectUrl = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = objectUrl;
    anchor.download = filename;

    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();

    URL.revokeObjectURL(objectUrl);
}


function bytesToHex(bytes) {
    return Array.from(bytes)
        .map((value) => value.toString(16).padStart(2, "0"))
        .join("");
}


async function calculateSha256(bytes) {
    const digest = await window.crypto.subtle.digest(
        "SHA-256",
        bytes
    );

    return bytesToHex(new Uint8Array(digest));
}



function providerNameFor(providerId) {
    const provider = state.providers.find(
        (candidate) => candidate.provider_id === providerId
    );

    return provider?.provider_name || providerId || "Unknown provider";
}


function providerIdentityUrl(providerId) {
    return (
        `/providers/${encodeURIComponent(providerId)}` +
        "/.well-known/gap.json"
    );
}


function readActiveProviderKey(providerDocument) {
    if (!Array.isArray(providerDocument?.keys)) {
        return null;
    }

    return (
        providerDocument.keys.find(
            (key) => key.key_id === providerDocument.active_key_id
        ) ||
        providerDocument.keys.find((key) => key.status === "active") ||
        providerDocument.keys[0] ||
        null
    );
}


async function readProviderDocument(providerId) {
    if (!providerId) {
        throw new Error("No provider was selected.");
    }

    if (state.providerDocuments[providerId]) {
        return state.providerDocuments[providerId];
    }

    const response = await fetch(providerIdentityUrl(providerId));

    if (!response.ok) {
        throw new Error(
            `Identity document resolution failed for ${providerId}.`
        );
    }

    const providerDocument = await response.json();

    if (providerDocument.provider_id !== providerId) {
        throw new Error(
            "The resolved identity document declared a different provider ID."
        );
    }

    state.providerDocuments[providerId] = providerDocument;

    return providerDocument;
}


async function fingerprintPublicKey(encodedPublicKey) {
    if (!encodedPublicKey) {
        return null;
    }

    try {
        const normalizedKey = encodedPublicKey.replace(/\s+/g, "");
        return await calculateSha256(base64ToBytes(normalizedKey));
    } catch {
        return null;
    }
}


function abbreviateFingerprint(fingerprint) {
    if (!fingerprint) {
        return "Unavailable";
    }

    return (
        `${fingerprint.slice(0, 16)}…` +
        fingerprint.slice(-16)
    );
}


function formatLifecycleDate(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
    });
}


function keyStatusClass(status) {
    if (["active", "retired", "revoked"].includes(status)) {
        return `key-status-${status}`;
    }

    return "key-status-unknown";
}


function describeKeyInventory(providerDocument) {
    const counts = {
        active: 0,
        retired: 0,
        revoked: 0,
    };

    (providerDocument?.keys || []).forEach((key) => {
        if (Object.hasOwn(counts, key.status)) {
            counts[key.status] += 1;
        }
    });

    return (
        `${counts.active} active · ${counts.retired} retired · ` +
        `${counts.revoked} revoked`
    );
}


async function createProviderKeyHistoryItem(key, activeKeyId) {
    const item = document.createElement("article");
    const heading = document.createElement("div");
    const headingCopy = document.createElement("div");
    const keyId = document.createElement("code");
    const role = document.createElement("small");
    const status = document.createElement("span");
    const metadata = document.createElement("div");
    const fingerprint = await fingerprintPublicKey(key.public_key);

    item.className = "provider-key-history-item";
    heading.className = "provider-key-history-item-heading";
    metadata.className = "provider-key-history-metadata";
    status.className = `key-status-pill ${keyStatusClass(key.status)}`;

    keyId.textContent = key.key_id;
    role.textContent = key.key_id === activeKeyId
        ? "Current issuance key"
        : key.status === "retired"
            ? "Historical verification key"
            : key.status === "revoked"
                ? "Rejected verification key"
                : "Published verification key";
    status.textContent = key.status || "unknown";

    headingCopy.append(keyId, role);
    heading.append(headingCopy, status);

    appendProviderMetric(metadata, "Algorithm", key.algorithm || "Not declared");
    appendProviderMetric(
        metadata,
        "Created",
        formatLifecycleDate(key.created_at)
    );

    if (key.status === "retired") {
        appendProviderMetric(
            metadata,
            "Retired",
            formatLifecycleDate(key.retired_at)
        );
    }

    if (key.status === "revoked") {
        appendProviderMetric(
            metadata,
            "Revoked",
            formatLifecycleDate(key.revoked_at)
        );
        appendProviderMetric(
            metadata,
            "Reason",
            key.revocation_reason || "Not declared"
        );
    }

    appendProviderMetric(
        metadata,
        "Fingerprint",
        abbreviateFingerprint(fingerprint)
    );

    item.append(heading, metadata);

    return item;
}


async function renderProviderKeyHistory(providerDocument) {
    const keys = Array.isArray(providerDocument?.keys)
        ? providerDocument.keys
        : [];

    elements.selectedProviderKeyCount.textContent = (
        `${keys.length} key${keys.length === 1 ? "" : "s"} · ` +
        describeKeyInventory(providerDocument)
    );

    if (keys.length === 0) {
        elements.selectedProviderKeyHistory.textContent = (
            "No verification keys were published."
        );
        return;
    }

    const items = await Promise.all(
        keys.map((key) => createProviderKeyHistoryItem(
            key,
            providerDocument.active_key_id
        ))
    );

    elements.selectedProviderKeyHistory.replaceChildren(...items);
}


async function renderSelectedProvider(providerId) {
    if (!providerId) {
        elements.providerIdentityCard.classList.add("hidden");
        return;
    }

    elements.providerIdentityCard.classList.remove("hidden");
    elements.selectedProviderName.textContent = providerNameFor(providerId);
    elements.selectedProviderId.textContent = providerId;
    elements.selectedProviderGapVersion.textContent = "Resolving…";
    elements.selectedProviderKeyId.textContent = "Resolving…";
    elements.selectedProviderAlgorithm.textContent = "Resolving…";
    elements.selectedProviderKeyStatus.textContent = "Resolving…";
    elements.selectedProviderFingerprint.textContent = "Resolving…";
    elements.selectedProviderKeyCount.textContent = "Resolving…";
    elements.selectedProviderKeyHistory.textContent = "";

    setBadge(
        elements.selectedProviderStatus,
        "Resolving identity",
        "neutral"
    );

    elements.selectedProviderIdentityLink.href = (
        providerIdentityUrl(providerId)
    );

    try {
        const providerDocument = await readProviderDocument(providerId);
        const verificationKey = readActiveProviderKey(providerDocument);
        const fingerprint = await fingerprintPublicKey(
            verificationKey?.public_key
        );

        state.selectedProviderDocument = providerDocument;

        elements.selectedProviderName.textContent = (
            providerDocument.provider_name
        );
        elements.selectedProviderId.textContent = (
            providerDocument.provider_id
        );
        elements.selectedProviderGapVersion.textContent = (
            providerDocument.gap_version
        );
        elements.selectedProviderKeyId.textContent = (
            verificationKey?.key_id || "No key published"
        );
        elements.selectedProviderAlgorithm.textContent = (
            verificationKey?.algorithm || "Not declared"
        );
        elements.selectedProviderKeyStatus.textContent = (
            verificationKey?.status || "Not declared"
        );
        elements.selectedProviderFingerprint.textContent = (
            abbreviateFingerprint(fingerprint)
        );
        elements.selectedProviderFingerprint.title = fingerprint || "";

        await renderProviderKeyHistory(providerDocument);

        setBadge(
            elements.selectedProviderStatus,
            "Identity resolved",
            "success"
        );
    } catch (error) {
        state.selectedProviderDocument = null;

        elements.selectedProviderGapVersion.textContent = "Unavailable";
        elements.selectedProviderKeyId.textContent = "Unavailable";
        elements.selectedProviderAlgorithm.textContent = "Unavailable";
        elements.selectedProviderKeyStatus.textContent = "Unavailable";
        elements.selectedProviderFingerprint.textContent = "Unavailable";
        elements.selectedProviderKeyCount.textContent = "Unavailable";
        elements.selectedProviderKeyHistory.textContent = "";

        setBadge(
            elements.selectedProviderStatus,
            "Resolution failed",
            "error"
        );

        setMessage(
            elements.generationError,
            error.message || "Provider identity could not be resolved.",
            "warning"
        );
    }
}


function appendProviderMetric(container, label, value) {
    const metric = document.createElement("div");
    const metricLabel = document.createElement("span");
    const metricValue = document.createElement("code");

    metricLabel.textContent = label;
    metricValue.textContent = value;

    metric.append(metricLabel, metricValue);
    container.append(metric);
}


async function createProviderEcosystemCard(provider) {
    const card = document.createElement("article");
    const heading = document.createElement("div");
    const marker = document.createElement("span");
    const headingCopy = document.createElement("div");
    const name = document.createElement("h3");
    const identifier = document.createElement("code");
    const metrics = document.createElement("div");
    const actionRow = document.createElement("div");
    const identityLink = document.createElement("a");
    const selectButton = document.createElement("button");

    card.className = "provider-ecosystem-card";
    heading.className = "provider-ecosystem-card-heading";
    marker.className = "provider-domain-marker";
    metrics.className = "provider-ecosystem-metrics";
    actionRow.className = "provider-ecosystem-actions";
    identityLink.className = "provider-identity-link";
    selectButton.className = "secondary-button compact-button";

    marker.textContent = provider.provider_name
        .split(/\s+/)
        .map((word) => word[0])
        .join("")
        .slice(0, 3)
        .toUpperCase();
    name.textContent = provider.provider_name;
    identifier.textContent = provider.provider_id;

    headingCopy.append(name, identifier);
    heading.append(marker, headingCopy);

    identityLink.href = providerIdentityUrl(provider.provider_id);
    identityLink.target = "_blank";
    identityLink.rel = "noreferrer";
    identityLink.textContent = "Identity document";

    selectButton.type = "button";
    selectButton.textContent = "Use this provider";
    selectButton.addEventListener(
        "click",
        async () => {
            elements.providerId.value = provider.provider_id;
            await renderSelectedProvider(provider.provider_id);
            activateTab("generate");
            elements.providerId.focus();
        }
    );

    actionRow.append(identityLink, selectButton);

    try {
        const providerDocument = await readProviderDocument(
            provider.provider_id
        );
        const verificationKey = readActiveProviderKey(providerDocument);
        const fingerprint = await fingerprintPublicKey(
            verificationKey?.public_key
        );

        appendProviderMetric(
            metrics,
            "GAP version",
            providerDocument.gap_version
        );
        appendProviderMetric(
            metrics,
            "Active key",
            providerDocument.active_key_id ||
                verificationKey?.key_id ||
                "Not published"
        );
        appendProviderMetric(
            metrics,
            "Key inventory",
            describeKeyInventory(providerDocument)
        );
        appendProviderMetric(
            metrics,
            "Algorithm",
            verificationKey?.algorithm || "Not declared"
        );
        appendProviderMetric(
            metrics,
            "Fingerprint",
            abbreviateFingerprint(fingerprint)
        );

        card.classList.add("provider-ecosystem-card-resolved");
    } catch {
        appendProviderMetric(
            metrics,
            "Identity document",
            "Resolution failed"
        );

        card.classList.add("provider-ecosystem-card-error");
    }

    card.append(heading, metrics, actionRow);

    return card;
}


async function renderProviderEcosystem() {
    elements.providerEcosystemGrid.replaceChildren();

    if (state.providers.length === 0) {
        setBadge(
            elements.providerEcosystemStatus,
            "No providers",
            "error"
        );
        return;
    }

    setBadge(
        elements.providerEcosystemStatus,
        "Resolving identities",
        "neutral"
    );

    const cards = await Promise.all(
        state.providers.map(createProviderEcosystemCard)
    );

    elements.providerEcosystemGrid.append(...cards);

    setBadge(
        elements.providerEcosystemStatus,
        `${cards.length} providers discovered`,
        "success"
    );
}


async function loadProviders() {
    state.providersReady = false;
    elements.providerId.disabled = true;
    setLoading(false);

    setBadge(
        elements.providerEcosystemStatus,
        "Discovering providers",
        "neutral"
    );

    try {
        const response = await fetch("/providers");

        if (!response.ok) {
            throw new Error(await readError(response));
        }

        const providers = await response.json();

        if (!Array.isArray(providers) || providers.length === 0) {
            throw new Error(
                "The GAP provider registry did not return any providers."
            );
        }

        state.providers = providers.filter(
            (provider) => (
                typeof provider.provider_id === "string" &&
                typeof provider.provider_name === "string"
            )
        );

        if (state.providers.length === 0) {
            throw new Error(
                "The GAP provider registry returned no usable providers."
            );
        }

        const options = state.providers.map((provider) => {
            const option = document.createElement("option");

            option.value = provider.provider_id;
            option.textContent = (
                `${provider.provider_name} · ${provider.provider_id}`
            );

            return option;
        });

        elements.providerId.replaceChildren(...options);
        elements.providerId.disabled = false;

        state.providersReady = true;
        setLoading(false);

        const selectedProviderId = elements.providerId.value;

        await Promise.all([
            renderSelectedProvider(selectedProviderId),
            renderProviderEcosystem(),
        ]);
    } catch (error) {
        state.providers = [];
        state.providersReady = false;

        const option = document.createElement("option");
        option.value = "";
        option.textContent = "Provider discovery failed";

        elements.providerId.replaceChildren(option);
        elements.providerId.disabled = true;

        setLoading(false);

        setBadge(
            elements.providerEcosystemStatus,
            "Registry unavailable",
            "error"
        );

        setMessage(
            elements.generationError,
            (
                error.message ||
                "Participating providers could not be discovered."
            ),
            "error"
        );
    }
}


function findArtifactDescriptor(credential) {
    const artifacts = credential?.payload?.artifacts;

    if (!Array.isArray(artifacts) || artifacts.length === 0) {
        return null;
    }

    return artifacts[0];
}


function readDescriptorHash(descriptor) {
    if (!descriptor) {
        return null;
    }

    const candidates = [
        descriptor.sha256,
        descriptor.sha256_digest,
        descriptor.artifact_hash,
        descriptor.hash,
        descriptor.digest,
    ];

    const directValue = candidates.find(
        (value) => typeof value === "string"
    );

    if (directValue) {
        return directValue.toLowerCase();
    }

    if (
        descriptor.digest &&
        typeof descriptor.digest.value === "string"
    ) {
        return descriptor.digest.value.toLowerCase();
    }

    return null;
}


function readDescriptorMediaType(descriptor) {
    return (
        descriptor?.media_type ||
        descriptor?.content_type ||
        "Not declared"
    );
}


function readGeneratedAt(payload) {
    return (
        payload?.generation?.generated_at ||
        payload?.generation?.created_at ||
        payload?.issued_at ||
        "Not declared"
    );
}


function setCheck(icon, detail, passed, passedText, failedText) {
    icon.textContent = passed ? "✓" : "×";
    icon.classList.toggle("check-success", passed);
    icon.classList.toggle("check-error", !passed);
    detail.textContent = passed ? passedText : failedText;
}


function setTimelineState(element, status, detail) {
    element.classList.remove(
        "timeline-success",
        "timeline-error",
        "timeline-active"
    );

    if (status) {
        element.classList.add(`timeline-${status}`);
    }

    element.querySelector("small").textContent = detail;
}


function setTrustNode(element, detailElement, status, detail) {
    element.classList.remove(
        "trust-success",
        "trust-error",
        "trust-active"
    );

    if (status) {
        element.classList.add(`trust-${status}`);
    }

    detailElement.textContent = detail;
}


function resetTrustChain() {
    const providerId = (
        state.credential?.payload?.provider?.provider_id ||
        null
    );

    setBadge(
        elements.trustChainStatus,
        "Awaiting verification",
        "neutral"
    );

    setTrustNode(
        elements.trustCredentialNode,
        elements.trustCredentialProvider,
        null,
        providerId
            ? `${providerNameFor(providerId)} · ${providerId}`
            : "Awaiting credential"
    );
    setTrustNode(
        elements.trustIdentityNode,
        elements.trustIdentityDocument,
        null,
        "Not resolved"
    );
    setTrustNode(
        elements.trustKeyNode,
        elements.trustKeyId,
        null,
        "Not resolved"
    );
    setTrustNode(
        elements.trustSignatureNode,
        elements.trustSignatureResult,
        null,
        "Not checked"
    );
}


function resetVerificationDisplay() {
    setBadge(
        elements.completeVerificationStatus,
        "Not verified",
        "neutral"
    );

    elements.verificationResultIcon.textContent = "?";
    elements.verificationResultIcon.className = (
        "verification-result-icon"
    );
    elements.verificationResultTitle.textContent = (
        "Awaiting verification"
    );
    elements.verificationResultDescription.textContent = (
        "Supply an artifact and credential to begin."
    );

    [
        [elements.signatureCheckIcon, elements.signatureCheckDetail],
        [elements.artifactCheckIcon, elements.artifactCheckDetail],
        [elements.providerCheckIcon, elements.providerCheckDetail],
    ].forEach(([icon, detail]) => {
        icon.textContent = "○";
        icon.className = "check-icon";
        detail.textContent = "Not checked";
    });

    [
        elements.timelineArtifact,
        elements.timelineHash,
        elements.timelineCompare,
        elements.timelineSignature,
        elements.timelineProvider,
    ].forEach((item) => {
        item.className = "";
        item.querySelector("small").textContent = "Awaiting input";
    });

    resetTrustChain();
}


function renderExplorer() {
    if (!state.credential) {
        elements.explorerEmpty.classList.remove("hidden");
        elements.explorerContent.classList.add("hidden");
        return;
    }

    const credential = state.credential;
    const payload = credential.payload;
    const descriptor = findArtifactDescriptor(credential);

    elements.explorerEmpty.classList.add("hidden");
    elements.explorerContent.classList.remove("hidden");

    elements.explorerCredentialId.textContent = (
        payload.credential_id || "Not declared"
    );
    elements.explorerGenerationId.textContent = (
        payload.generation?.generation_id || "Not declared"
    );
    elements.explorerGeneratedAt.textContent = readGeneratedAt(payload);
    elements.explorerProviderId.textContent = (
        payload.provider?.provider_id || "Not declared"
    );
    elements.explorerModelId.textContent = (
        payload.model?.model_id || "Not declared"
    );
    elements.explorerMediaType.textContent = (
        readDescriptorMediaType(descriptor)
    );
    elements.explorerArtifactHash.textContent = (
        readDescriptorHash(descriptor) || "Not declared"
    );
    elements.explorerAlgorithm.textContent = (
        credential.proof?.type || "Not declared"
    );
    elements.explorerKeyId.textContent = (
        credential.proof?.key_id || "Not declared"
    );
    elements.credentialJson.textContent = JSON.stringify(
        credential,
        null,
        2
    );

    setBadge(
        elements.explorerSignatureStatus,
        "Not verified",
        "neutral"
    );
}


function renderGenerationResult(result) {
    const artifactBytes = base64ToBytes(result.artifact_base64);

    state.artifactBase64 = result.artifact_base64;
    state.artifactBytes = artifactBytes;
    state.artifactFilename = result.filename;
    state.artifactMediaType = result.media_type;
    state.credential = result.credential;
    state.originalArtifactBytes = new Uint8Array(artifactBytes);
    state.originalCredential = cloneValue(result.credential);
    state.providerSubstitution = null;
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    const payload = result.credential.payload;

    elements.emptyState.classList.add("hidden");
    elements.resultContent.classList.remove("hidden");

    elements.artifactImage.src = (
        `data:${result.media_type};base64,${result.artifact_base64}`
    );
    elements.artifactFilename.textContent = result.filename;
    elements.artifactMediaType.textContent = result.media_type;
    elements.artifactProvider.textContent = (
        payload.provider.provider_name ||
        providerNameFor(payload.provider.provider_id)
    );
    elements.artifactModel.textContent = payload.model.model_id;

    setBadge(
        elements.generationStatus,
        "Credential issued",
        "success"
    );

    elements.artifactUploadName.textContent = result.filename;
    elements.credentialUploadName.textContent = (
        `${payload.generation.generation_id}-credential.json`
    );

    renderExplorer();
    resetVerificationDisplay();
}


async function readError(response) {
    try {
        const body = await response.json();

        if (typeof body.detail === "string") {
            return body.detail;
        }

        if (Array.isArray(body.detail)) {
            return body.detail
                .map((entry) => entry.msg)
                .join(" ");
        }

        return JSON.stringify(body);
    } catch {
        return `Request failed with status ${response.status}.`;
    }
}


async function generateArtifact(event) {
    event.preventDefault();

    hideMessage(elements.generationError);
    setLoading(true);

    setBadge(
        elements.generationStatus,
        "Generating",
        "neutral"
    );

    const requestBody = {
        provider_id: elements.providerId.value,
        account_reference: elements.accountReference.value.trim(),
        prompt: elements.prompt.value.trim(),
        retention_days: Number(elements.retentionDays.value),
    };

    try {
        const response = await fetch(
            "/generations/create",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(requestBody),
            }
        );

        if (!response.ok) {
            throw new Error(await readError(response));
        }

        renderGenerationResult(await response.json());
    } catch (error) {
        setBadge(
            elements.generationStatus,
            "Generation failed",
            "error"
        );

        setMessage(
            elements.generationError,
            error.message || "The artifact could not be generated.",
            "error"
        );
    } finally {
        setLoading(false);
    }
}


async function verifyCredentialSignature(credential) {
    const response = await fetch(
        "/credentials/verify",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                credential,
            }),
        }
    );

    if (!response.ok) {
        throw new Error(await readError(response));
    }

    return response.json();
}


async function runCompleteVerification() {
    hideMessage(elements.verificationError);

    if (!state.artifactBytes || !state.credential) {
        setMessage(
            elements.verificationError,
            "Supply both an artifact and a credential before verification.",
            "warning"
        );
        return;
    }

    elements.runVerificationButton.disabled = true;
    elements.runVerificationButton.textContent = "Verifying";

    resetVerificationDisplay();

    try {
        setTimelineState(
            elements.timelineArtifact,
            "active",
            "Reading supplied artifact bytes"
        );

        const suppliedBytes = state.artifactBytes;

        setTimelineState(
            elements.timelineArtifact,
            "success",
            `${suppliedBytes.length.toLocaleString()} bytes loaded`
        );

        setTimelineState(
            elements.timelineHash,
            "active",
            "Calculating SHA-256 digest"
        );

        const calculatedHash = await calculateSha256(suppliedBytes);

        setTimelineState(
            elements.timelineHash,
            "success",
            calculatedHash
        );

        const descriptor = findArtifactDescriptor(state.credential);
        const expectedHash = readDescriptorHash(descriptor);

        setTimelineState(
            elements.timelineCompare,
            "active",
            "Comparing calculated and declared digests"
        );

        const artifactMatches = (
            Boolean(expectedHash) &&
            calculatedHash === expectedHash
        );

        setTimelineState(
            elements.timelineCompare,
            artifactMatches ? "success" : "error",
            artifactMatches
                ? "Artifact digest matches"
                : "Artifact digest mismatch"
        );

        setCheck(
            elements.artifactCheckIcon,
            elements.artifactCheckDetail,
            artifactMatches,
            "Calculated SHA-256 matches the credential.",
            expectedHash
                ? "Calculated SHA-256 does not match the credential."
                : "No supported artifact digest was found."
        );

        const credentialProviderId = (
            state.credential.payload?.provider?.provider_id ||
            null
        );
        const credentialKeyId = (
            state.credential.proof?.key_id ||
            null
        );
        const credentialAlgorithm = (
            state.credential.proof?.type ||
            "Not declared"
        );

        setTrustNode(
            elements.trustCredentialNode,
            elements.trustCredentialProvider,
            credentialProviderId ? "success" : "error",
            credentialProviderId
                ? (
                    `${providerNameFor(credentialProviderId)} · ` +
                    credentialProviderId
                )
                : "No provider ID was declared"
        );

        setTrustNode(
            elements.trustIdentityNode,
            elements.trustIdentityDocument,
            "active",
            "Resolving public identity document"
        );

        let providerDocument = null;
        let verificationKey = null;
        let identityResolved = false;
        let keyResolved = false;

        try {
            providerDocument = await readProviderDocument(
                credentialProviderId
            );
            identityResolved = (
                providerDocument.provider_id === credentialProviderId
            );

            setTrustNode(
                elements.trustIdentityNode,
                elements.trustIdentityDocument,
                identityResolved ? "success" : "error",
                identityResolved
                    ? (
                        `${providerDocument.provider_name} · ` +
                        providerIdentityUrl(credentialProviderId)
                    )
                    : "Identity document provider mismatch"
            );

            verificationKey = providerDocument.keys?.find(
                (key) => key.key_id === credentialKeyId
            ) || null;

            keyResolved = Boolean(
                verificationKey &&
                verificationKey.status !== "revoked"
            );

            const keyLifecycleDetail = verificationKey
                ? (
                    `${verificationKey.key_id} · ` +
                    `${verificationKey.algorithm} · ` +
                    `${verificationKey.status}`
                )
                : null;

            setTrustNode(
                elements.trustKeyNode,
                elements.trustKeyId,
                keyResolved ? "success" : "error",
                keyResolved
                    ? keyLifecycleDetail
                    : verificationKey?.status === "revoked"
                        ? `${keyLifecycleDetail} · explicitly rejected`
                        : credentialKeyId
                            ? `Key ${credentialKeyId} is not published here`
                            : "No signing key ID was declared"
            );
        } catch (error) {
            setTrustNode(
                elements.trustIdentityNode,
                elements.trustIdentityDocument,
                "error",
                error.message || "Identity document resolution failed"
            );
            setTrustNode(
                elements.trustKeyNode,
                elements.trustKeyId,
                "error",
                "Verification key could not be resolved"
            );
        }

        setTimelineState(
            elements.timelineSignature,
            "active",
            "Verifying signed credential payload"
        );

        setTrustNode(
            elements.trustSignatureNode,
            elements.trustSignatureResult,
            "active",
            `Checking ${credentialAlgorithm} signature`
        );

        let verification = null;
        let signatureValid = false;
        let providerValid = false;

        try {
            verification = await verifyCredentialSignature(
                state.credential
            );

            state.lastVerification = verification;

            signatureValid = verification.valid === true;
            providerValid = Boolean(
                verification.provider_id &&
                identityResolved &&
                keyResolved
            );

            const resolvedAlgorithm = (
                verification.algorithm ||
                verificationKey?.algorithm ||
                credentialAlgorithm
            );

            setTimelineState(
                elements.timelineSignature,
                signatureValid ? "success" : "error",
                signatureValid
                    ? `${resolvedAlgorithm} signature valid`
                    : "Credential signature invalid"
            );

            setTimelineState(
                elements.timelineProvider,
                providerValid ? "success" : "error",
                providerValid
                    ? `Resolved ${verification.provider_id}`
                    : "Provider identity or signing key was rejected"
            );

            setTrustNode(
                elements.trustSignatureNode,
                elements.trustSignatureResult,
                signatureValid ? "success" : "error",
                signatureValid
                    ? `${resolvedAlgorithm} signature accepted`
                    : `${resolvedAlgorithm} signature rejected`
            );
        } catch (error) {
            state.lastVerification = null;

            setTimelineState(
                elements.timelineSignature,
                "error",
                "Credential verification request failed"
            );

            setTimelineState(
                elements.timelineProvider,
                "error",
                error.message
            );

            setTrustNode(
                elements.trustSignatureNode,
                elements.trustSignatureResult,
                "error",
                error.message || "Verification request failed"
            );
        }

        setCheck(
            elements.signatureCheckIcon,
            elements.signatureCheckDetail,
            signatureValid,
            "Ed25519 credential signature is valid.",
            "Credential signature validation failed."
        );

        setCheck(
            elements.providerCheckIcon,
            elements.providerCheckDetail,
            providerValid,
            "Provider identity and an allowed signing-key state were resolved.",
            "Provider identity or signing-key lifecycle state was rejected."
        );

        const completeResult = (
            artifactMatches &&
            signatureValid &&
            providerValid
        );

        setBadge(
            elements.trustChainStatus,
            signatureValid && providerValid
                ? "Trust established"
                : "Trust rejected",
            signatureValid && providerValid
                ? "success"
                : "error"
        );

        setBadge(
            elements.completeVerificationStatus,
            completeResult ? "Valid" : "Invalid",
            completeResult ? "success" : "error"
        );

        elements.verificationResultIcon.textContent = (
            completeResult ? "✓" : "×"
        );
        elements.verificationResultIcon.className = (
            "verification-result-icon " +
            (
                completeResult
                    ? "verification-result-success"
                    : "verification-result-error"
            )
        );

        elements.verificationResultTitle.textContent = (
            completeResult
                ? "Artifact successfully verified"
                : "Verification failed"
        );

        if (!completeResult && state.providerSubstitution) {
            const substitution = state.providerSubstitution;

            elements.verificationResultDescription.textContent = (
                `Provider substitution detected. The credential was issued ` +
                `by ${substitution.expectedName} ` +
                `(${substitution.expectedId}) but now presents ` +
                `${substitution.presentedName} ` +
                `(${substitution.presentedId}). The presented provider's ` +
                `verification key cannot validate the original signature.`
            );
        } else if (
            !completeResult &&
            state.revokedKeySubstitution &&
            verification?.failure_reason === "revoked-key"
        ) {
            elements.verificationResultDescription.textContent = (
                `Revoked key rejected. ${state.revokedKeySubstitution.keyId} ` +
                `remains published by ${state.revokedKeySubstitution.providerName} ` +
                `with revocation metadata, so GAP refuses the credential before ` +
                `accepting its signature.`
            );
        } else {
            elements.verificationResultDescription.textContent = (
                completeResult
                    ? (
                        "The artifact digest, credential signature and provider " +
                        "identity are all valid."
                    )
                    : (
                        "One or more GAP verification controls detected an " +
                        "invalid or modified input."
                    )
            );
        }

        renderExplorer();

        setBadge(
            elements.explorerSignatureStatus,
            signatureValid ? "Signature valid" : "Signature invalid",
            signatureValid ? "success" : "error"
        );
    } catch (error) {
        setBadge(
            elements.trustChainStatus,
            "Verification failed",
            "error"
        );

        setMessage(
            elements.verificationError,
            error.message || "Verification could not be completed.",
            "error"
        );
    } finally {
        elements.runVerificationButton.disabled = false;
        elements.runVerificationButton.textContent = (
            "Run complete verification"
        );
    }
}



async function readArtifactUpload(event) {
    const file = event.target.files[0];

    if (!file) {
        return;
    }

    state.artifactBytes = new Uint8Array(await file.arrayBuffer());
    state.artifactFilename = file.name;
    state.artifactMediaType = file.type || "application/octet-stream";
    state.originalArtifactBytes = new Uint8Array(state.artifactBytes);
    state.providerSubstitution = null;
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    elements.artifactUploadName.textContent = file.name;

    resetVerificationDisplay();
}


async function readCredentialUpload(event) {
    const file = event.target.files[0];

    if (!file) {
        return;
    }

    try {
        const credential = JSON.parse(await file.text());

        state.credential = credential;
        state.originalCredential = cloneValue(credential);
        state.providerSubstitution = null;
        state.revokedKeySubstitution = null;
        state.lastVerification = null;

        elements.credentialUploadName.textContent = file.name;

        renderExplorer();
        resetVerificationDisplay();
    } catch {
        setMessage(
            elements.verificationError,
            "The selected credential is not valid JSON.",
            "error"
        );
    }
}


function useLatestGeneratedArtifact() {
    if (
        !state.originalArtifactBytes ||
        !state.originalCredential
    ) {
        setMessage(
            elements.verificationError,
            "Generate an artifact before using this shortcut.",
            "warning"
        );
        return;
    }

    state.artifactBytes = new Uint8Array(
        state.originalArtifactBytes
    );
    state.credential = cloneValue(state.originalCredential);
    state.providerSubstitution = null;
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    elements.artifactUploadName.textContent = (
        state.artifactFilename || "Generated artifact"
    );
    elements.credentialUploadName.textContent = (
        "Generated credential"
    );

    hideMessage(elements.verificationError);
    hideMessage(elements.tamperMessage);

    renderExplorer();
    resetVerificationDisplay();
}


function tamperArtifact() {
    if (!state.artifactBytes) {
        setMessage(
            elements.tamperMessage,
            "Load an artifact before attempting the tamper demonstration.",
            "warning"
        );
        return;
    }

    const modifiedBytes = new Uint8Array(state.artifactBytes);
    const index = Math.max(
        0,
        Math.min(modifiedBytes.length - 1, 128)
    );

    modifiedBytes[index] ^= 1;
    state.artifactBytes = modifiedBytes;
    state.providerSubstitution = null;
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    setMessage(
        elements.tamperMessage,
        (
            "One bit in the supplied artifact has been changed. Run " +
            "verification again: the artifact hash should fail while the " +
            "credential signature remains valid."
        ),
        "warning"
    );

    resetVerificationDisplay();
}


function tamperCredential() {
    if (!state.credential) {
        setMessage(
            elements.tamperMessage,
            "Load a credential before attempting the tamper demonstration.",
            "warning"
        );
        return;
    }

    state.credential = cloneValue(state.credential);

    const currentModelId = (
        state.credential.payload?.model?.model_id ||
        "unknown-model"
    );

    state.credential.payload.model.model_id = (
        `${currentModelId}-tampered`
    );
    state.providerSubstitution = null;
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    renderExplorer();

    setMessage(
        elements.tamperMessage,
        (
            "The signed model ID has been changed. Run verification again: " +
            "the credential signature should fail."
        ),
        "warning"
    );

    resetVerificationDisplay();
}


function tamperProviderIdentity() {
    if (!state.credential) {
        setMessage(
            elements.tamperMessage,
            "Load a credential before substituting its provider identity.",
            "warning"
        );
        return;
    }

    const currentProvider = (
        state.credential.payload?.provider ||
        null
    );

    if (!currentProvider?.provider_id) {
        setMessage(
            elements.tamperMessage,
            "The credential does not declare a provider identity.",
            "warning"
        );
        return;
    }

    const replacement = state.providers.find(
        (provider) => provider.provider_id !== currentProvider.provider_id
    );

    if (!replacement) {
        setMessage(
            elements.tamperMessage,
            "At least two participating providers are required for this demo.",
            "warning"
        );
        return;
    }

    const originalProvider = (
        state.originalCredential?.payload?.provider ||
        currentProvider
    );

    state.credential = cloneValue(state.credential);
    state.credential.payload.provider.provider_id = replacement.provider_id;
    state.credential.payload.provider.provider_name = replacement.provider_name;

    state.providerSubstitution = {
        expectedId: originalProvider.provider_id,
        expectedName: (
            originalProvider.provider_name ||
            providerNameFor(originalProvider.provider_id)
        ),
        presentedId: replacement.provider_id,
        presentedName: replacement.provider_name,
    };
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    renderExplorer();

    setMessage(
        elements.tamperMessage,
        (
            `The credential now presents ${replacement.provider_name} ` +
            `(${replacement.provider_id}) instead of ` +
            `${state.providerSubstitution.expectedName} ` +
            `(${state.providerSubstitution.expectedId}). The signed payload ` +
            `was not re-signed. Run verification to demonstrate provider ` +
            `isolation.`
        ),
        "warning"
    );

    resetVerificationDisplay();
}


async function tamperRevokedKey() {
    if (!state.credential) {
        setMessage(
            elements.tamperMessage,
            "Load a credential before referencing a revoked key.",
            "warning"
        );
        return;
    }

    const providerId = state.credential.payload?.provider?.provider_id;

    if (!providerId) {
        setMessage(
            elements.tamperMessage,
            "The credential does not declare a provider identity.",
            "warning"
        );
        return;
    }

    try {
        const providerDocument = await readProviderDocument(providerId);
        const revokedKey = providerDocument.keys?.find(
            (key) => key.status === "revoked"
        );

        if (!revokedKey) {
            setMessage(
                elements.tamperMessage,
                (
                    `${providerDocument.provider_name} does not publish a ` +
                    `revoked key. Select GAP Demo Provider for this demonstration.`
                ),
                "warning"
            );
            return;
        }

        state.credential = cloneValue(state.credential);
        state.credential.proof.key_id = revokedKey.key_id;
        state.providerSubstitution = null;
        state.revokedKeySubstitution = {
            keyId: revokedKey.key_id,
            providerId,
            providerName: providerDocument.provider_name,
            reason: revokedKey.revocation_reason,
        };
        state.lastVerification = null;

        renderExplorer();

        setMessage(
            elements.tamperMessage,
            (
                `The credential now references revoked key ${revokedKey.key_id}. ` +
                `Run verification again: GAP should reject it with the ` +
                `revoked-key decision before signature acceptance.`
            ),
            "warning"
        );

        resetVerificationDisplay();
    } catch (error) {
        setMessage(
            elements.tamperMessage,
            error.message || "The provider key history could not be resolved.",
            "warning"
        );
    }
}


function restoreVerificationInputs() {
    if (state.originalArtifactBytes) {
        state.artifactBytes = new Uint8Array(
            state.originalArtifactBytes
        );
    }

    if (state.originalCredential) {
        state.credential = cloneValue(state.originalCredential);
    }

    state.providerSubstitution = null;
    state.revokedKeySubstitution = null;
    state.lastVerification = null;

    hideMessage(elements.tamperMessage);
    renderExplorer();
    resetVerificationDisplay();
}


function openGeneratedVerification() {
    useLatestGeneratedArtifact();
    activateTab("verify");
}


function downloadArtifact() {
    if (!state.artifactBytes || !state.artifactFilename) {
        return;
    }

    downloadBlob(
        bytesToBlob(
            state.artifactBytes,
            state.artifactMediaType || "application/octet-stream"
        ),
        state.artifactFilename
    );
}


function downloadCredential() {
    if (!state.credential) {
        return;
    }

    const generationId = (
        state.credential.payload?.generation?.generation_id ||
        "gap-generation"
    );

    downloadBlob(
        new Blob(
            [JSON.stringify(state.credential, null, 2)],
            {
                type: "application/json",
            }
        ),
        `${generationId}-credential.json`
    );
}


async function copyCredential() {
    if (!state.credential) {
        return;
    }

    try {
        await navigator.clipboard.writeText(
            JSON.stringify(state.credential, null, 2)
        );

        const originalText = elements.copyCredentialButton.textContent;
        elements.copyCredentialButton.textContent = "Copied";

        window.setTimeout(
            () => {
                elements.copyCredentialButton.textContent = originalText;
            },
            1400
        );
    } catch {
        elements.copyCredentialButton.textContent = "Copy unavailable";
    }
}


async function verifyExplorerCredential() {
    if (!state.credential) {
        return;
    }

    elements.explorerVerifyButton.disabled = true;
    elements.explorerVerifyButton.textContent = "Verifying";

    try {
        const result = await verifyCredentialSignature(state.credential);

        setBadge(
            elements.explorerSignatureStatus,
            result.valid ? "Signature valid" : "Signature invalid",
            result.valid ? "success" : "error"
        );
    } catch {
        setBadge(
            elements.explorerSignatureStatus,
            "Verification failed",
            "error"
        );
    } finally {
        elements.explorerVerifyButton.disabled = false;
        elements.explorerVerifyButton.textContent = "Verify signature";
    }
}


async function checkServiceHealth() {
    try {
        const response = await fetch("/health");

        if (!response.ok) {
            throw new Error("Health check failed.");
        }

        const health = await response.json();

        setBadge(
            elements.serviceStatus,
            health.status === "healthy"
                ? `Online · v${health.version}`
                : "Service degraded",
            health.status === "healthy"
                ? "success"
                : "error"
        );
    } catch {
        setBadge(
            elements.serviceStatus,
            "Service unavailable",
            "error"
        );
    }
}


elements.tabButtons.forEach((button) => {
    button.addEventListener(
        "click",
        () => activateTab(button.dataset.tabTarget)
    );
});

elements.providerId.addEventListener(
    "change",
    async () => {
        hideMessage(elements.generationError);
        await renderSelectedProvider(elements.providerId.value);
    }
);


elements.generationForm.addEventListener(
    "submit",
    generateArtifact
);

elements.prompt.addEventListener(
    "input",
    updatePromptCount
);

elements.downloadArtifactButton.addEventListener(
    "click",
    downloadArtifact
);

elements.downloadCredentialButton.addEventListener(
    "click",
    downloadCredential
);

elements.openVerificationButton.addEventListener(
    "click",
    openGeneratedVerification
);

elements.artifactFileInput.addEventListener(
    "change",
    readArtifactUpload
);

elements.credentialFileInput.addEventListener(
    "change",
    readCredentialUpload
);

elements.useGeneratedButton.addEventListener(
    "click",
    useLatestGeneratedArtifact
);

elements.runVerificationButton.addEventListener(
    "click",
    runCompleteVerification
);

elements.tamperArtifactButton.addEventListener(
    "click",
    tamperArtifact
);

elements.tamperCredentialButton.addEventListener(
    "click",
    tamperCredential
);

elements.tamperProviderButton.addEventListener(
    "click",
    tamperProviderIdentity
);

elements.tamperRevokedKeyButton.addEventListener(
    "click",
    tamperRevokedKey
);

elements.restoreVerificationButton.addEventListener(
    "click",
    restoreVerificationInputs
);

elements.copyCredentialButton.addEventListener(
    "click",
    copyCredential
);

elements.explorerVerifyButton.addEventListener(
    "click",
    verifyExplorerCredential
);


updatePromptCount();
resetVerificationDisplay();
renderExplorer();
setLoading(false);
checkServiceHealth();
loadProviders();