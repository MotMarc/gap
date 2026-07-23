"use strict";


function requireElement(id) {
    const element = document.getElementById(id);

    if (!element) {
        throw new Error(`Required DOM element is missing: ${id}`);
    }

    return element;
}


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
    providerTrustDocuments: {},
    registryAuthorityDocuments: {},
    trustRegistry: [],
    providersReady: false,
    trustRegistryReady: false,
    selectedProviderDocument: null,
    selectedProviderTrust: null,
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
    selectedProviderTrustStatus: document.querySelector(
        "#selected-provider-trust-status"
    ),
    selectedProviderTrustDecision: document.querySelector(
        "#selected-provider-trust-decision"
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
    trustRegistryNode: document.querySelector("#trust-registry-node"),
    trustRegistryResult: document.querySelector("#trust-registry-result"),
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
    registryCheckIcon: document.querySelector("#registry-check-icon"),
    registryCheckDetail: document.querySelector("#registry-check-detail"),
    attestationCheckIcon: requireElement("attestation-check-icon"),
    attestationCheckDetail: requireElement("attestation-check-detail"),
    authorityCheckIcon: requireElement("authority-check-icon"),
    authorityCheckDetail: requireElement("authority-check-detail"),
    overallCheckIcon: requireElement("overall-check-icon"),
    overallCheckDetail: requireElement("overall-check-detail"),
    timelineArtifact: document.querySelector("#timeline-artifact"),
    timelineHash: document.querySelector("#timeline-hash"),
    timelineCompare: document.querySelector("#timeline-compare"),
    timelineSignature: document.querySelector("#timeline-signature"),
    timelineProvider: document.querySelector("#timeline-provider"),
    timelineRegistry: document.querySelector("#timeline-registry"),
    timelineAuthorityIdentity: requireElement("timeline-authority-identity"),
    timelineAuthorityKey: requireElement("timeline-authority-key"),
    timelineAttestation: requireElement("timeline-attestation"),
    timelineFederationChain: requireElement("timeline-federation-chain"),
    timelineFederationConflict: requireElement("timeline-federation-conflict"),
    timelineOverall: requireElement("timeline-overall"),
    federationBundleGrid: requireElement("federation-bundle-grid"),
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
    trustRegistryGrid: document.querySelector("#trust-registry-grid"),
    trustRegistryStatus: document.querySelector("#trust-registry-status"),
    registryAuthorityGrid: document.querySelector("#registry-authority-grid"),
    trustAttestationGrid: document.querySelector("#trust-attestation-grid"),
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
        "status-warning",
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
    const selectedProviderApproved = Boolean(
        state.selectedProviderTrust?.trusted === true &&
        state.selectedProviderTrust?.status === "approved"
    );

    elements.generateButton.disabled = (
        isLoading ||
        !state.providersReady ||
        !selectedProviderApproved
    );
    elements.generateButton.classList.toggle("is-loading", isLoading);

    const label = elements.generateButton.querySelector(".button-label");

    if (!state.providersReady) {
        label.textContent = "Discovering approved providers";
        return;
    }

    if (!selectedProviderApproved) {
        label.textContent = "Provider is not approved";
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


function providerTrustUrl(providerId) {
    return `/providers/${encodeURIComponent(providerId)}/trust`;
}


function registryAuthorityIdentityUrl(authorityId) {
    return (
        `/registry-authorities/${encodeURIComponent(authorityId)}` +
        "/.well-known/gap-registry.json"
    );
}


function trustStatusLabel(status) {
    const labels = {
        "self-declared": "Self-declared",
        applicant: "Applicant",
        approved: "Approved",
        suspended: "Suspended",
        removed: "Removed",
    };

    return labels[status] || status || "Unknown";
}


function trustStatusClass(status) {
    const knownStatuses = [
        "self-declared",
        "applicant",
        "approved",
        "suspended",
        "removed",
    ];

    return knownStatuses.includes(status)
        ? `trust-status-${status}`
        : "trust-status-unknown";
}


function badgeStatusForTrust(status) {
    if (status === "approved") {
        return "success";
    }

    if (status === "applicant" || status === "self-declared") {
        return "warning";
    }

    return "error";
}


function formatRegistryDate(value) {
    if (!value) {
        return "No decision recorded";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}


async function readProviderTrust(providerId) {
    if (!providerId) {
        throw new Error("No provider was selected.");
    }

    if (state.providerTrustDocuments[providerId]) {
        return state.providerTrustDocuments[providerId];
    }

    const response = await fetch(providerTrustUrl(providerId));

    if (!response.ok) {
        throw new Error(
            `Registry trust resolution failed for ${providerId}.`
        );
    }

    const trustDocument = await response.json();

    if (trustDocument.provider_id !== providerId) {
        throw new Error(
            "The registry response declared a different provider ID."
        );
    }

    state.providerTrustDocuments[providerId] = trustDocument;

    return trustDocument;
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


async function readRegistryAuthorityDocument(authorityId) {
    if (!authorityId) {
        throw new Error("Registry authority was not declared.");
    }

    if (state.registryAuthorityDocuments[authorityId]) {
        return state.registryAuthorityDocuments[authorityId];
    }

    const response = await fetch(registryAuthorityIdentityUrl(authorityId));

    if (!response.ok) {
        if (response.status === 404) {
            throw new Error(`Unknown registry authority: ${authorityId}`);
        }
        throw new Error("Registry authority identity could not be resolved.");
    }

    const document = await response.json();

    if (document.authority_id !== authorityId) {
        throw new Error("Registry authority identity mismatch.");
    }

    state.registryAuthorityDocuments[authorityId] = document;
    return document;
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
        state.selectedProviderDocument = null;
        state.selectedProviderTrust = null;
        elements.providerIdentityCard.classList.add("hidden");
        setLoading(false);
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
    elements.selectedProviderTrustStatus.textContent = "Resolving…";
    elements.selectedProviderTrustDecision.textContent = "Resolving…";
    elements.selectedProviderKeyCount.textContent = "Resolving…";
    elements.selectedProviderKeyHistory.textContent = "";

    state.selectedProviderDocument = null;
    state.selectedProviderTrust = null;

    setBadge(
        elements.selectedProviderStatus,
        "Resolving identity and trust",
        "neutral"
    );

    elements.selectedProviderIdentityLink.href = (
        providerIdentityUrl(providerId)
    );

    let identityResolved = false;
    let trustResolved = false;

    try {
        const providerDocument = await readProviderDocument(providerId);
        const verificationKey = readActiveProviderKey(providerDocument);
        const fingerprint = await fingerprintPublicKey(
            verificationKey?.public_key
        );

        state.selectedProviderDocument = providerDocument;
        identityResolved = true;

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
    } catch (error) {
        elements.selectedProviderGapVersion.textContent = "Unavailable";
        elements.selectedProviderKeyId.textContent = "Unavailable";
        elements.selectedProviderAlgorithm.textContent = "Unavailable";
        elements.selectedProviderKeyStatus.textContent = "Unavailable";
        elements.selectedProviderFingerprint.textContent = "Unavailable";
        elements.selectedProviderKeyCount.textContent = "Unavailable";
        elements.selectedProviderKeyHistory.textContent = "";

        setMessage(
            elements.generationError,
            error.message || "Provider identity could not be resolved.",
            "warning"
        );
    }

    try {
        const trustDocument = await readProviderTrust(providerId);

        state.selectedProviderTrust = trustDocument;
        trustResolved = true;

        elements.selectedProviderTrustStatus.textContent = (
            `${trustStatusLabel(trustDocument.status)} · ` +
            (trustDocument.trusted ? "trusted" : "not trusted")
        );

        const latestDecision = trustDocument.latest_decision;

        elements.selectedProviderTrustDecision.textContent = latestDecision
            ? (
                `${latestDecision.decision_id} · ` +
                `${latestDecision.authority} · ` +
                formatRegistryDate(latestDecision.decided_at)
            )
            : "No authoritative decision recorded";
    } catch (error) {
        elements.selectedProviderTrustStatus.textContent = "Unavailable";
        elements.selectedProviderTrustDecision.textContent = (
            "Registry resolution failed"
        );

        setMessage(
            elements.generationError,
            error.message || "Provider registry trust could not be resolved.",
            "warning"
        );
    }

    const providerApproved = Boolean(
        identityResolved &&
        trustResolved &&
        state.selectedProviderTrust?.trusted === true &&
        state.selectedProviderTrust?.status === "approved"
    );

    if (providerApproved) {
        setBadge(
            elements.selectedProviderStatus,
            "Identity resolved · Approved",
            "success"
        );
    } else if (identityResolved && trustResolved) {
        const trustStatus = state.selectedProviderTrust?.status;

        setBadge(
            elements.selectedProviderStatus,
            `Identity resolved · ${trustStatusLabel(trustStatus)}`,
            badgeStatusForTrust(trustStatus)
        );
    } else {
        setBadge(
            elements.selectedProviderStatus,
            "Resolution failed",
            "error"
        );
    }

    setLoading(false);
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
    const trustBadge = document.createElement("span");
    const metrics = document.createElement("div");
    const actionRow = document.createElement("div");
    const identityLink = document.createElement("a");
    const trustLink = document.createElement("a");
    const selectButton = document.createElement("button");

    card.className = "provider-ecosystem-card";
    heading.className = "provider-ecosystem-card-heading";
    marker.className = "provider-domain-marker";
    metrics.className = "provider-ecosystem-metrics";
    actionRow.className = "provider-ecosystem-actions";
    identityLink.className = "provider-identity-link";
    trustLink.className = "provider-identity-link";
    selectButton.className = "secondary-button compact-button";
    trustBadge.className = (
        `trust-status-pill ${trustStatusClass(provider.trust_status)}`
    );

    marker.textContent = provider.provider_name
        .split(/\s+/)
        .map((word) => word[0])
        .join("")
        .slice(0, 3)
        .toUpperCase();
    name.textContent = provider.provider_name;
    identifier.textContent = provider.provider_id;
    trustBadge.textContent = trustStatusLabel(provider.trust_status);

    headingCopy.append(name, identifier);
    heading.append(marker, headingCopy, trustBadge);

    identityLink.href = providerIdentityUrl(provider.provider_id);
    identityLink.target = "_blank";
    identityLink.rel = "noreferrer";
    identityLink.textContent = "Identity document";

    trustLink.href = providerTrustUrl(provider.provider_id);
    trustLink.target = "_blank";
    trustLink.rel = "noreferrer";
    trustLink.textContent = "Registry trust";

    const selectable = Boolean(
        provider.provider_trusted === true &&
        provider.trust_status === "approved"
    );

    selectButton.type = "button";
    selectButton.textContent = selectable
        ? "Use this provider"
        : "Issuance unavailable";
    selectButton.disabled = !selectable;

    if (selectable) {
        selectButton.addEventListener(
            "click",
            async () => {
                elements.providerId.value = provider.provider_id;
                await renderSelectedProvider(provider.provider_id);
                activateTab("generate");
                elements.providerId.focus();
            }
        );
    }

    actionRow.append(identityLink, trustLink, selectButton);

    appendProviderMetric(
        metrics,
        "Registry trust",
        `${trustStatusLabel(provider.trust_status)} · ` +
            (provider.provider_trusted ? "trusted" : "not trusted")
    );

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
        "Resolving identities and trust",
        "neutral"
    );

    const cards = await Promise.all(
        state.providers.map(createProviderEcosystemCard)
    );

    elements.providerEcosystemGrid.append(...cards);

    const approvedCount = state.providers.filter(
        (provider) => (
            provider.provider_trusted === true &&
            provider.trust_status === "approved"
        )
    ).length;

    setBadge(
        elements.providerEcosystemStatus,
        `${cards.length} providers · ${approvedCount} approved`,
        approvedCount > 0 ? "success" : "warning"
    );
}


function createTrustDecisionItem(decision) {
    const item = document.createElement("li");
    const heading = document.createElement("div");
    const status = document.createElement("span");
    const date = document.createElement("small");
    const reason = document.createElement("p");
    const authority = document.createElement("code");

    status.className = (
        `trust-status-pill ${trustStatusClass(decision.status)}`
    );
    status.textContent = trustStatusLabel(decision.status);
    date.textContent = formatRegistryDate(decision.decided_at);
    reason.textContent = decision.reason;
    authority.textContent = (
        `${decision.authority} · ${decision.decision_id}`
    );

    heading.append(status, date);
    item.append(heading, reason, authority);

    return item;
}


async function createTrustRegistryCard(entry) {
    const card = document.createElement("article");
    const heading = document.createElement("div");
    const headingCopy = document.createElement("div");
    const name = document.createElement("h3");
    const identifier = document.createElement("code");
    const trustBadge = document.createElement("span");
    const summary = document.createElement("p");
    const metrics = document.createElement("div");
    const historyHeading = document.createElement("h4");
    const history = document.createElement("ol");
    const trustLink = document.createElement("a");

    card.className = "trust-registry-card";
    heading.className = "trust-registry-card-heading";
    metrics.className = "trust-registry-card-metrics";
    history.className = "trust-decision-history";
    trustBadge.className = (
        `trust-status-pill ${trustStatusClass(entry.status)}`
    );
    trustLink.className = "provider-identity-link";

    name.textContent = entry.provider_name;
    identifier.textContent = entry.provider_id;
    trustBadge.textContent = trustStatusLabel(entry.status);
    summary.textContent = entry.trusted
        ? (
            "This provider is currently approved. Its active key may issue " +
            "new GAP credentials."
        )
        : (
            "This provider is not currently trusted for new credential " +
            "issuance."
        );

    appendProviderMetric(
        metrics,
        "Current status",
        trustStatusLabel(entry.status)
    );
    appendProviderMetric(
        metrics,
        "Trusted",
        entry.trusted ? "Yes" : "No"
    );
    appendProviderMetric(
        metrics,
        "Latest decision",
        entry.latest_decision_id || "No decision recorded"
    );
    appendProviderMetric(
        metrics,
        "Decision time",
        formatRegistryDate(entry.latest_decision_at)
    );

    historyHeading.textContent = "Public decision history";
    trustLink.href = providerTrustUrl(entry.provider_id);
    trustLink.target = "_blank";
    trustLink.rel = "noreferrer";
    trustLink.textContent = "Open provider trust record";

    headingCopy.append(name, identifier);
    heading.append(headingCopy, trustBadge);

    try {
        const trustDocument = await readProviderTrust(entry.provider_id);
        const historyItems = (
            trustDocument.decision_history || []
        ).map(createTrustDecisionItem);

        if (historyItems.length > 0) {
            history.append(...historyItems);
        } else {
            const emptyItem = document.createElement("li");
            emptyItem.textContent = "No public trust decisions recorded.";
            history.append(emptyItem);
        }
    } catch (error) {
        const errorItem = document.createElement("li");
        errorItem.textContent = (
            error.message || "Decision history could not be resolved."
        );
        history.append(errorItem);
        card.classList.add("trust-registry-card-error");
    }

    card.append(
        heading,
        summary,
        metrics,
        historyHeading,
        history,
        trustLink
    );

    return card;
}


async function renderTrustRegistry() {
    elements.trustRegistryGrid.replaceChildren();
    state.trustRegistryReady = false;

    setBadge(
        elements.trustRegistryStatus,
        "Loading registry",
        "neutral"
    );

    try {
        const response = await fetch("/trust-registry");

        if (!response.ok) {
            throw new Error(await readError(response));
        }

        const entries = await response.json();

        if (!Array.isArray(entries)) {
            throw new Error("The trust registry returned an invalid response.");
        }

        state.trustRegistry = entries;
        state.trustRegistryReady = true;

        if (entries.length === 0) {
            elements.trustRegistryGrid.textContent = (
                "No providers are currently recorded in the trust registry."
            );
            setBadge(
                elements.trustRegistryStatus,
                "Registry empty",
                "warning"
            );
            return;
        }

        const cards = await Promise.all(
            entries.map(createTrustRegistryCard)
        );

        elements.trustRegistryGrid.append(...cards);

        const approvedCount = entries.filter(
            (entry) => entry.status === "approved" && entry.trusted
        ).length;

        setBadge(
            elements.trustRegistryStatus,
            `${entries.length} recorded · ${approvedCount} approved`,
            approvedCount > 0 ? "success" : "warning"
        );
    } catch (error) {
        state.trustRegistry = [];
        state.trustRegistryReady = false;
        elements.trustRegistryGrid.textContent = (
            error.message || "The GAP Trust Registry is unavailable."
        );

        setBadge(
            elements.trustRegistryStatus,
            "Registry unavailable",
            "error"
        );
    }
}


function createRegistryDetail(label, value) {
    const detail = document.createElement("p");
    const title = document.createElement("strong");
    const text = document.createElement("span");

    title.textContent = `${label}: `;
    text.textContent = value ?? "Unavailable";
    detail.append(title, text);

    return detail;
}


function createRegistryAuthorityCard(authority, identityDocument) {
    const card = document.createElement("article");
    const name = document.createElement("h3");
    const identifier = document.createElement("code");
    const identityLink = document.createElement("a");
    const trusted = authority.trusted_by_local_registry === true;
    const keys = Array.isArray(identityDocument?.keys)
        ? identityDocument.keys
        : [];
    const lifecycle = keys.length > 0
        ? keys.map((key) => `${key.key_id}: ${key.status}`).join(", ")
        : "Unavailable";

    card.className = (
        `${trusted ? "authority-trusted" : "authority-untrusted"} credential-card`
    );
    name.textContent = authority.authority_name;
    identifier.textContent = authority.authority_id;
    identityLink.href = (
        `/registry-authorities/${encodeURIComponent(authority.authority_id)}` +
        "/.well-known/gap-registry.json"
    );
    identityLink.textContent = "Registry authority identity";

    card.append(
        name,
        identifier,
        createRegistryDetail("Active authority key", authority.active_key_id),
        createRegistryDetail(
            "Published key count",
            String(authority.published_key_count)
        ),
        createRegistryDetail(
            "Trusted local authority",
            trusted ? "Yes" : "No"
        ),
        createRegistryDetail("Authority key lifecycle", lifecycle),
        identityLink
    );

    return card;
}


function createTrustAttestationCard(attestation, trustEntries, authorities) {
    const card = document.createElement("article");
    const heading = document.createElement("h3");
    const payload = attestation.payload ?? {};
    const proof = attestation.proof ?? {};
    const trustEntry = trustEntries.find(
        (entry) => entry.latest_decision_id === payload.decision_id
    );
    const authority = authorities.find(
        (entry) => entry.authority_id === payload.registry_authority_id
    );
    const isCurrent = trustEntry?.trust_attestation_id === payload.attestation_id;
    const attestationValid = (
        isCurrent && trustEntry?.trust_attestation_valid === true
    );
    const authorityTrusted = authority?.trusted_by_local_registry === true;

    card.className = (
        `${attestationValid ? "attestation-valid" : "attestation-historical"} ` +
        "credential-card"
    );
    heading.textContent = payload.attestation_id ?? "Unknown attestation";

    card.append(
        heading,
        createRegistryDetail("Decision ID", payload.decision_id),
        createRegistryDetail("Provider ID", payload.provider_id),
        createRegistryDetail("Provider status", payload.status),
        createRegistryDetail(
            "Registry authority ID",
            payload.registry_authority_id
        ),
        createRegistryDetail("Authority signing key", proof.key_id),
        createRegistryDetail(
            "Authority key status",
            isCurrent ? trustEntry?.authority_key_status : "Historical"
        ),
        createRegistryDetail("Issued", payload.issued_at),
        createRegistryDetail(
            "Attestation validity",
            isCurrent
                ? (attestationValid ? "Valid" : "Invalid")
                : "Historical — not the current provider decision"
        ),
        createRegistryDetail(
            "Registry-authority trust",
            authorityTrusted ? "Trusted locally" : "Not trusted locally"
        )
    );

    return card;
}


async function readJsonCollection(url, panel, failureLabel) {
    let response;
    try {
        response = await fetch(url);
    } catch {
        panel.textContent = `${failureLabel} network request failed.`;
        return null;
    }

    if (!response.ok) {
        panel.textContent = `${failureLabel} request failed (${response.status}).`;
        return null;
    }

    let data;
    try {
        data = await response.json();
    } catch {
        panel.textContent = `${failureLabel} returned invalid JSON.`;
        return null;
    }

    if (!Array.isArray(data)) {
        panel.textContent = `${failureLabel} returned an invalid response.`;
        return null;
    }

    return data;
}


async function renderRegistryAuthorities() {
    const authorities = await readJsonCollection(
        "/registry-authorities",
        elements.registryAuthorityGrid,
        "Registry authority"
    );
    if (authorities === null) return;

    const identityDocuments = await Promise.all(
        authorities.map(async (authority) => {
            const url = (
                `/registry-authorities/${encodeURIComponent(authority.authority_id)}` +
                "/.well-known/gap-registry.json"
            );
            try {
                const response = await fetch(url);
                return response.ok ? await response.json() : null;
            } catch {
                return null;
            }
        })
    );
    const cards = authorities.map(
        (authority, index) => createRegistryAuthorityCard(
            authority,
            identityDocuments[index]
        )
    );
    elements.registryAuthorityGrid.replaceChildren(...cards);
}


async function renderTrustAttestations() {
    const results = await Promise.all([
        readJsonCollection(
            "/trust-attestations",
            elements.trustAttestationGrid,
            "Trust attestation"
        ),
        readJsonCollection(
            "/trust-registry",
            elements.trustAttestationGrid,
            "Trust registry"
        ),
        readJsonCollection(
            "/registry-authorities",
            elements.trustAttestationGrid,
            "Registry authority"
        )
    ]);
    if (results.some((result) => result === null)) return;

    const [attestations, trustEntries, authorities] = results;
    const cards = attestations.map(
        (attestation) => createTrustAttestationCard(
            attestation,
            trustEntries,
            authorities
        )
    );
    elements.trustAttestationGrid.replaceChildren(...cards);
}


async function loadProviders() {
    state.providersReady = false;
    state.selectedProviderTrust = null;
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
                typeof provider.provider_name === "string" &&
                typeof provider.trust_status === "string" &&
                typeof provider.provider_trusted === "boolean"
            )
        );

        if (state.providers.length === 0) {
            throw new Error(
                "The GAP provider registry returned no usable providers."
            );
        }

        const selectableProviders = state.providers.filter(
            (provider) => (
                provider.provider_trusted === true &&
                provider.trust_status === "approved"
            )
        );

        if (selectableProviders.length === 0) {
            throw new Error(
                "No approved providers are currently available for issuance."
            );
        }

        const options = selectableProviders.map((provider) => {
            const option = document.createElement("option");

            option.value = provider.provider_id;
            option.textContent = (
                `${provider.provider_name} · Approved · ` +
                provider.provider_id
            );

            return option;
        });

        elements.providerId.replaceChildren(...options);
        elements.providerId.disabled = false;

        state.providersReady = true;

        const selectedProviderId = elements.providerId.value;

        await Promise.all([
            renderSelectedProvider(selectedProviderId),
            renderProviderEcosystem(),
        ]);

        setLoading(false);
    } catch (error) {
        state.providers = [];
        state.providersReady = false;
        state.selectedProviderTrust = null;

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
    setTrustNode(
        elements.trustRegistryNode,
        elements.trustRegistryResult,
        null,
        "Not resolved"
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
        [elements.registryCheckIcon, elements.registryCheckDetail],
        [elements.attestationCheckIcon, elements.attestationCheckDetail],
        [elements.authorityCheckIcon, elements.authorityCheckDetail],
        [elements.overallCheckIcon, elements.overallCheckDetail],
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
        elements.timelineRegistry,
        elements.timelineAuthorityIdentity,
        elements.timelineAuthorityKey,
        elements.timelineAttestation,
        elements.timelineFederationChain,
        elements.timelineFederationConflict,
        elements.timelineOverall,
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

        setTimelineState(
            elements.timelineRegistry,
            "active",
            "Resolving independent provider trust"
        );
        setTimelineState(
            elements.timelineAuthorityIdentity,
            "active",
            "Resolving registry-authority identity"
        );
        setTimelineState(
            elements.timelineAuthorityKey,
            "active",
            "Resolving authority signing-key lifecycle"
        );
        setTimelineState(
            elements.timelineAttestation,
            "active",
            "Verifying signed trust attestation"
        );
        setTimelineState(
            elements.timelineFederationChain,
            "active",
            "Checking accepted bundle freshness and chain"
        );
        setTimelineState(
            elements.timelineFederationConflict,
            "active",
            "Comparing authority decisions"
        );
        setTimelineState(
            elements.timelineOverall,
            "active",
            "Calculating overall GAP validity"
        );

        setTrustNode(
            elements.trustRegistryNode,
            elements.trustRegistryResult,
            "active",
            "Querying the GAP Trust Registry"
        );

        let verification = null;
        let signatureValid = false;
        let providerValid = false;
        let registryTrusted = false;
        let registryStatus = "self-declared";
        let attestationPresent = false;
        let attestationValid = false;
        let authorityTrusted = false;
        let authorityIdentityResolved = false;
        let authorityKeyAllowed = false;
        let authorityKeyStatus = null;
        let backendOverallValid = false;

        try {
            verification = await verifyCredentialSignature(
                state.credential
            );

            state.lastVerification = verification;

            signatureValid = verification.cryptographic_valid === true;
            providerValid = Boolean(
                verification.provider_id === credentialProviderId &&
                identityResolved &&
                keyResolved
            );
            registryTrusted = verification.provider_trusted === true;
            registryStatus = (
                verification.provider_trust_status ||
                "self-declared"
            );
            attestationPresent = (
                verification.trust_attestation_present === true
            );
            attestationValid = (
                verification.trust_attestation_valid === true
            );
            authorityTrusted = (
                verification.registry_authority_trusted === true
            );
            authorityKeyStatus = (
                verification.registry_authority_key_status ||
                null
            );
            backendOverallValid = verification.valid === true;

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
                    : (
                        verification.failure_reason ||
                        "Credential signature invalid"
                    )
            );

            setTimelineState(
                elements.timelineProvider,
                providerValid ? "success" : "error",
                providerValid
                    ? `Resolved ${verification.provider_id}`
                    : "Provider identity or signing key was rejected"
            );

            setTimelineState(
                elements.timelineRegistry,
                registryTrusted ? "success" : "error",
                registryTrusted
                    ? (
                        `${trustStatusLabel(registryStatus)} · ` +
                        `${verification.trust_decision_id || "decision recorded"}`
                    )
                    : (
                        `${trustStatusLabel(registryStatus)} · ` +
                        "provider is not currently trusted"
                    )
            );

            let authorityDocument = null;

            if (
                attestationPresent &&
                verification.registry_authority_id
            ) {
                try {
                    authorityDocument = await readRegistryAuthorityDocument(
                        verification.registry_authority_id
                    );
                    authorityIdentityResolved = Boolean(
                        authorityTrusted &&
                        authorityDocument.authority_id === (
                            verification.registry_authority_id
                        )
                    );
                    setTimelineState(
                        elements.timelineAuthorityIdentity,
                        authorityIdentityResolved ? "success" : "error",
                        authorityIdentityResolved
                            ? (
                                `${authorityDocument.authority_name} · ` +
                                authorityDocument.authority_id
                            )
                            : (
                                `Unknown registry authority: ` +
                                verification.registry_authority_id
                            )
                    );
                } catch (error) {
                    setTimelineState(
                        elements.timelineAuthorityIdentity,
                        "error",
                        error.message ||
                            "Registry authority identity could not be resolved"
                    );
                }
            } else {
                setTimelineState(
                    elements.timelineAuthorityIdentity,
                    "error",
                    attestationPresent
                        ? "Registry authority was not declared"
                        : "No signed trust attestation is present"
                );
            }

            const authorityKey = authorityDocument?.keys?.find(
                (key) => key.key_id === verification.registry_authority_key_id
            ) || null;
            authorityKeyAllowed = Boolean(
                authorityIdentityResolved &&
                authorityKey &&
                authorityKey.status === authorityKeyStatus &&
                ["active", "retired"].includes(authorityKeyStatus)
            );

            let authorityKeyDetail = "Authority signing key could not be resolved";
            if (authorityKeyStatus === "revoked") {
                authorityKeyDetail = (
                    `${verification.registry_authority_key_id || "Unknown key"} · ` +
                    "revoked · explicitly rejected"
                );
            } else if (authorityKeyAllowed) {
                authorityKeyDetail = (
                    `${verification.registry_authority_key_id} · ` +
                    `${authorityKeyStatus}` +
                    (
                        authorityKeyStatus === "retired"
                            ? " · historical verification allowed"
                            : ""
                    )
                );
            }

            setTimelineState(
                elements.timelineAuthorityKey,
                authorityKeyAllowed ? "success" : "error",
                authorityKeyDetail
            );

            const attestationAccepted = Boolean(
                attestationPresent &&
                attestationValid &&
                authorityTrusted &&
                authorityKeyAllowed
            );
            const attestationFailureDetails = {
                "missing-trust-attestation": "Missing signed trust attestation",
                "invalid-attestation-signature": "Invalid attestation signature",
                "attestation-decision-mismatch": (
                    "Attestation does not match the current trust decision"
                ),
                "unknown-registry-authority": "Unknown registry authority",
                "unknown-authority-key": "Unknown registry-authority key",
                "revoked-authority-key": "Registry-authority key is revoked",
            };

            setTimelineState(
                elements.timelineAttestation,
                attestationAccepted ? "success" : "error",
                attestationAccepted
                    ? (
                        "Ed25519 attestation signature valid · " +
                        verification.trust_attestation_id
                    )
                    : (
                        attestationFailureDetails[
                            verification.trust_failure_reason
                        ] ||
                        verification.trust_failure_reason ||
                        "Trust attestation could not be validated"
                    )
            );
            const federationSources = verification.federation_sources || [];
            const federationBundleIds = verification.federation_bundle_ids || [];
            const federationConflict = verification.federation_conflict === true;
            const effectiveTrustStatus = (
                verification.effective_provider_trust_status || "unavailable"
            );
            setTimelineState(
                elements.timelineFederationChain,
                verification.federation_failure_reason &&
                    verification.federation_source_count === 0
                    ? "error"
                    : "success",
                federationBundleIds.length
                    ? `${federationBundleIds.length} current bundle source(s)`
                    : "Current local authority source; no portable bundle required"
            );
            setTimelineState(
                elements.timelineFederationConflict,
                federationConflict ? "error" : "success",
                federationConflict
                    ? `Authority disagreement: ${federationSources.map(
                        (source) => `${source.registry_authority_id}=${source.provider_status}`
                    ).join(", ")}`
                    : `No conflict · effective status ${effectiveTrustStatus}`
            );

            setTrustNode(
                elements.trustSignatureNode,
                elements.trustSignatureResult,
                signatureValid ? "success" : "error",
                signatureValid
                    ? `${resolvedAlgorithm} signature accepted`
                    : `${resolvedAlgorithm} signature rejected`
            );

            setTrustNode(
                elements.trustRegistryNode,
                elements.trustRegistryResult,
                registryTrusted ? "success" : "error",
                registryTrusted
                    ? (
                        `Approved by the GAP Trust Registry · ` +
                        `${verification.trust_decision_id || "decision recorded"}`
                    )
                    : (
                        `${trustStatusLabel(registryStatus)} · ` +
                        "not trusted for overall GAP validity"
                    )
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

            setTimelineState(
                elements.timelineRegistry,
                "error",
                "Registry trust could not be resolved"
            );
            setTimelineState(
                elements.timelineAuthorityIdentity,
                "error",
                "Registry authority identity could not be resolved"
            );
            setTimelineState(
                elements.timelineAuthorityKey,
                "error",
                "Authority signing key could not be resolved"
            );
            setTimelineState(
                elements.timelineAttestation,
                "error",
                "Trust attestation could not be verified"
            );
            setTimelineState(
                elements.timelineFederationChain,
                "error",
                "Federation bundle state could not be resolved"
            );
            setTimelineState(
                elements.timelineFederationConflict,
                "error",
                "Authority conflicts could not be evaluated"
            );
            setTimelineState(
                elements.timelineOverall,
                "error",
                "Overall GAP validity could not be calculated"
            );

            setTrustNode(
                elements.trustSignatureNode,
                elements.trustSignatureResult,
                "error",
                error.message || "Verification request failed"
            );

            setTrustNode(
                elements.trustRegistryNode,
                elements.trustRegistryResult,
                "error",
                "Registry trust resolution failed"
            );
        }

        setCheck(
            elements.signatureCheckIcon,
            elements.signatureCheckDetail,
            signatureValid,
            "Ed25519 credential signature is cryptographically valid.",
            "Credential signature validation failed."
        );

        setCheck(
            elements.providerCheckIcon,
            elements.providerCheckDetail,
            providerValid,
            "Provider identity and an allowed signing-key state were resolved.",
            "Provider identity or signing-key lifecycle state was rejected."
        );

        setCheck(
            elements.registryCheckIcon,
            elements.registryCheckDetail,
            registryTrusted,
            "Provider is currently approved by the GAP Trust Registry.",
            (
                `${trustStatusLabel(registryStatus)} providers are not ` +
                "trusted for overall GAP validity."
            )
        );

        setCheck(
            elements.attestationCheckIcon,
            elements.attestationCheckDetail,
            attestationValid,
            "The signed trust attestation is valid.",
            "The signed trust attestation is missing or invalid."
        );

        setCheck(
            elements.authorityCheckIcon,
            elements.authorityCheckDetail,
            authorityTrusted && authorityIdentityResolved && authorityKeyAllowed,
            "The registry authority and signing key are trusted locally.",
            "The registry authority or signing key is not trusted locally."
        );

        const completeResult = (
            artifactMatches &&
            signatureValid &&
            registryTrusted &&
            attestationValid &&
            authorityTrusted &&
            authorityIdentityResolved &&
            authorityKeyAllowed &&
            backendOverallValid
        );
        const authenticButUntrusted = (
            artifactMatches &&
            signatureValid &&
            providerValid &&
            !registryTrusted
        );

        let overallDetail = (
            "Artifact, credential, provider approval, attestation and " +
            "registry authority are valid"
        );
        if (!artifactMatches) {
            overallDetail = "Artifact digest mismatch";
        } else if (!signatureValid) {
            overallDetail = "Credential signature invalid";
        } else if (registryStatus !== "approved") {
            overallDetail = "Provider is not approved";
        } else if (!attestationPresent) {
            overallDetail = "Signed trust attestation is missing";
        } else if (authorityKeyStatus === "revoked") {
            overallDetail = "Registry-authority signing key is revoked";
        } else if (!attestationValid) {
            overallDetail = "Trust attestation signature is invalid";
        } else if (!authorityTrusted) {
            overallDetail = "Registry authority is not trusted";
        } else if (!authorityIdentityResolved || !authorityKeyAllowed) {
            overallDetail = "Registry-authority identity or key was not resolved";
        } else if (!registryTrusted) {
            overallDetail = "Provider signed trust could not be established";
        } else if (!backendOverallValid) {
            overallDetail = "Backend GAP validity policy rejected the credential";
        }

        setTimelineState(
            elements.timelineOverall,
            completeResult ? "success" : "error",
            overallDetail
        );

        setCheck(
            elements.overallCheckIcon,
            elements.overallCheckDetail,
            completeResult,
            overallDetail,
            overallDetail
        );

        setBadge(
            elements.trustChainStatus,
            completeResult
                ? "Trust established"
                : authenticButUntrusted
                    ? "Authentic · Registry rejected"
                    : "Trust rejected",
            completeResult
                ? "success"
                : authenticButUntrusted
                    ? "warning"
                    : "error"
        );

        setBadge(
            elements.completeVerificationStatus,
            completeResult
                ? "Valid and trusted"
                : authenticButUntrusted
                    ? "Authentic but untrusted"
                    : "Invalid",
            completeResult
                ? "success"
                : authenticButUntrusted
                    ? "warning"
                    : "error"
        );

        elements.verificationResultIcon.textContent = (
            completeResult
                ? "✓"
                : authenticButUntrusted
                    ? "!"
                    : "×"
        );
        elements.verificationResultIcon.className = (
            "verification-result-icon " +
            (
                completeResult
                    ? "verification-result-success"
                    : authenticButUntrusted
                        ? "verification-result-warning"
                        : "verification-result-error"
            )
        );

        elements.verificationResultTitle.textContent = (
            completeResult
                ? "Artifact successfully verified"
                : authenticButUntrusted
                    ? "Credential authentic, provider untrusted"
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
        } else if (authenticButUntrusted) {
            elements.verificationResultDescription.textContent = (
                `The artifact digest and credential signature are authentic, ` +
                `but the provider's registry status is ` +
                `${trustStatusLabel(registryStatus)}. Overall GAP validity ` +
                `therefore fails without changing the cryptographic result.`
            );
        } else {
            elements.verificationResultDescription.textContent = (
                completeResult
                    ? (
                        "The artifact digest, credential signature, provider " +
                        "identity and independent registry trust are all valid."
                    )
                    : (
                        "One or more GAP verification controls detected an " +
                        "invalid, modified or untrusted input."
                    )
            );
        }

        renderExplorer();

        setBadge(
            elements.explorerSignatureStatus,
            signatureValid
                ? registryTrusted
                    ? "Authentic and trusted"
                    : "Authentic · Provider untrusted"
                : "Cryptographically invalid",
            signatureValid
                ? registryTrusted
                    ? "success"
                    : "warning"
                : "error"
        );
    } catch (error) {
        [
            elements.timelineAuthorityIdentity,
            elements.timelineAuthorityKey,
            elements.timelineAttestation,
            elements.timelineFederationChain,
            elements.timelineFederationConflict,
            elements.timelineOverall,
        ].forEach((timeline) => {
            setTimelineState(
                timeline,
                "error",
                "Verification did not reach this stage"
            );
        });

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
        const cryptographicValid = result.cryptographic_valid === true;
        const providerTrusted = result.provider_trusted === true;

        setBadge(
            elements.explorerSignatureStatus,
            cryptographicValid
                ? providerTrusted
                    ? "Authentic and trusted"
                    : "Authentic · Provider untrusted"
                : "Cryptographically invalid",
            cryptographicValid
                ? providerTrusted
                    ? "success"
                    : "warning"
                : "error"
        );
    } catch {
        setBadge(
            elements.explorerSignatureStatus,
            "Verification failed",
            "error"
        );
    } finally {
        elements.explorerVerifyButton.disabled = false;
        elements.explorerVerifyButton.textContent = "Verify credential";
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


async function renderFederationBundles() {
    try {
        const response = await fetch("/federation/bundles");
        if (!response.ok) {
            throw new Error("Federation bundle list unavailable.");
        }
        const bundles = await response.json();
        elements.federationBundleGrid.replaceChildren();
        if (!bundles.length) {
            const empty = document.createElement("p");
            empty.textContent = (
                "No portable bundles accepted. Local signed trust remains active."
            );
            elements.federationBundleGrid.append(empty);
            return;
        }
        bundles.forEach((bundle) => {
            const card = document.createElement("article");
            card.className = "trust-registry-card";
            const title = document.createElement("strong");
            title.textContent = (
                `${bundle.registry_authority_id} · sequence ${bundle.sequence_number}`
            );
            const detail = document.createElement("p");
            detail.textContent = (
                `${bundle.bundle_id} · expires ${bundle.expires_at} · ` +
                `${bundle.attestation_count} attestations · ` +
                `${bundle.current ? "current" : bundle.expired ? "expired" : "historical"}`
            );
            const chain = document.createElement("small");
            chain.textContent = (
                `Digest ${bundle.bundle_hash}; predecessor ` +
                `${bundle.previous_bundle_hash || "genesis"}; signature ` +
                `${bundle.signature_valid ? "valid" : "invalid"}; chain ` +
                `${bundle.chain_valid ? "valid" : "invalid"}; replay protection active`
            );
            card.append(title, detail, chain);
            elements.federationBundleGrid.append(card);
        });
    } catch (error) {
        elements.federationBundleGrid.textContent = (
            error.message || "Federation bundle state could not be loaded."
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
renderTrustRegistry();
renderRegistryAuthorities();
renderTrustAttestations();
renderFederationBundles();
