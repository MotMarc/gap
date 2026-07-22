"use strict";


const state = {
    artifactBase64: null,
    artifactBytes: null,
    artifactFilename: null,
    artifactMediaType: null,
    credential: null,
    originalArtifactBytes: null,
    originalCredential: null,
};


const elements = {
    tabButtons: document.querySelectorAll("[data-tab-target]"),
    tabPages: document.querySelectorAll("[data-tab-page]"),
    generationForm: document.querySelector("#generation-form"),
    providerId: document.querySelector("#provider-id"),
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
    elements.generateButton.disabled = isLoading;
    elements.generateButton.classList.toggle("is-loading", isLoading);

    const label = elements.generateButton.querySelector(".button-label");

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

    const payload = result.credential.payload;

    elements.emptyState.classList.add("hidden");
    elements.resultContent.classList.remove("hidden");

    elements.artifactImage.src = (
        `data:${result.media_type};base64,${result.artifact_base64}`
    );
    elements.artifactFilename.textContent = result.filename;
    elements.artifactMediaType.textContent = result.media_type;
    elements.artifactProvider.textContent = payload.provider.provider_id;
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

        setTimelineState(
            elements.timelineSignature,
            "active",
            "Verifying signed credential payload"
        );

        let verification;
        let signatureValid = false;
        let providerValid = false;

        try {
            verification = await verifyCredentialSignature(
                state.credential
            );

            signatureValid = verification.valid === true;
            providerValid = Boolean(verification.provider_id);

            setTimelineState(
                elements.timelineSignature,
                signatureValid ? "success" : "error",
                signatureValid
                    ? `${verification.algorithm} signature valid`
                    : "Credential signature invalid"
            );

            setTimelineState(
                elements.timelineProvider,
                providerValid ? "success" : "error",
                providerValid
                    ? `Resolved ${verification.provider_id}`
                    : "Provider identity could not be resolved"
            );
        } catch (error) {
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
            "Provider identity and signing key were resolved.",
            "Provider identity could not be trusted."
        );

        const completeResult = (
            artifactMatches &&
            signatureValid &&
            providerValid
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

        if (state.credential === state.originalCredential) {
            renderExplorer();
        }

        setBadge(
            elements.explorerSignatureStatus,
            signatureValid ? "Signature valid" : "Signature invalid",
            signatureValid ? "success" : "error"
        );
    } catch (error) {
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


function restoreVerificationInputs() {
    if (state.originalArtifactBytes) {
        state.artifactBytes = new Uint8Array(
            state.originalArtifactBytes
        );
    }

    if (state.originalCredential) {
        state.credential = cloneValue(state.originalCredential);
    }

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
checkServiceHealth();