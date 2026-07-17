"use strict";


const state = {
    artifactBase64: null,
    artifactFilename: null,
    artifactMediaType: null,
    credential: null,
};


const elements = {
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
    credentialSection: document.querySelector("#credential-section"),
    credentialJson: document.querySelector("#credential-json"),
    generationId: document.querySelector("#generation-id"),
    credentialId: document.querySelector("#credential-id"),
    credentialAlgorithm: document.querySelector(
        "#credential-algorithm"
    ),
    credentialKeyId: document.querySelector("#credential-key-id"),
    copyCredentialButton: document.querySelector(
        "#copy-credential-button"
    ),
    verifyButton: document.querySelector("#verify-button"),
    verificationMessage: document.querySelector(
        "#verification-message"
    ),
};


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


function setLoading(isLoading) {
    elements.generateButton.disabled = isLoading;
    elements.generateButton.classList.toggle(
        "is-loading",
        isLoading
    );

    const label = elements.generateButton.querySelector(
        ".button-label"
    );

    label.textContent = isLoading
        ? "Generating artifact"
        : "Generate and issue credential";
}


function updatePromptCount() {
    const characterCount = elements.prompt.value.length;
    elements.promptCount.textContent = (
        `${characterCount.toLocaleString()} / 10,000`
    );
}


function base64ToBlob(base64Value, mediaType) {
    const byteCharacters = window.atob(base64Value);
    const byteNumbers = new Array(byteCharacters.length);

    for (
        let index = 0;
        index < byteCharacters.length;
        index += 1
    ) {
        byteNumbers[index] = byteCharacters.charCodeAt(index);
    }

    return new Blob(
        [new Uint8Array(byteNumbers)],
        {
            type: mediaType,
        }
    );
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


function renderGenerationResult(result) {
    state.artifactBase64 = result.artifact_base64;
    state.artifactFilename = result.filename;
    state.artifactMediaType = result.media_type;
    state.credential = result.credential;

    const credential = result.credential;
    const payload = credential.payload;

    elements.emptyState.classList.add("hidden");
    elements.resultContent.classList.remove("hidden");
    elements.credentialSection.classList.remove("hidden");

    elements.artifactImage.src = (
        `data:${result.media_type};base64,${result.artifact_base64}`
    );

    elements.artifactFilename.textContent = result.filename;
    elements.artifactMediaType.textContent = result.media_type;

    elements.artifactProvider.textContent = (
        payload.provider.provider_id
    );

    elements.artifactModel.textContent = payload.model.model_id;

    elements.generationId.textContent = (
        payload.generation.generation_id
    );

    elements.credentialId.textContent = payload.credential_id;
    elements.credentialAlgorithm.textContent = credential.proof.type;
    elements.credentialKeyId.textContent = credential.proof.key_id;

    elements.credentialJson.textContent = JSON.stringify(
        credential,
        null,
        2
    );

    hideMessage(elements.verificationMessage);

    setBadge(
        elements.generationStatus,
        "Credential issued",
        "success"
    );

    elements.credentialSection.scrollIntoView({
        behavior: "smooth",
        block: "start",
    });
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
    hideMessage(elements.verificationMessage);

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

        const result = await response.json();

        renderGenerationResult(result);
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


async function verifyCredential() {
    if (!state.credential) {
        setMessage(
            elements.verificationMessage,
            "Generate a credential before attempting verification.",
            "warning"
        );
        return;
    }

    elements.verifyButton.disabled = true;
    elements.verifyButton.textContent = "Verifying";

    hideMessage(elements.verificationMessage);

    try {
        const response = await fetch(
            "/credentials/verify",
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    credential: state.credential,
                }),
            }
        );

        if (!response.ok) {
            throw new Error(await readError(response));
        }

        const verification = await response.json();

        if (verification.valid) {
            setMessage(
                elements.verificationMessage,
                (
                    "Credential valid. The Ed25519 signature, provider " +
                    "identity and signing key were successfully verified."
                ),
                "success"
            );
        } else {
            setMessage(
                elements.verificationMessage,
                (
                    "Credential invalid. The credential payload or proof " +
                    "could not be verified."
                ),
                "error"
            );
        }
    } catch (error) {
        setMessage(
            elements.verificationMessage,
            error.message || "Credential verification failed.",
            "error"
        );
    } finally {
        elements.verifyButton.disabled = false;
        elements.verifyButton.textContent = "Verify credential";
    }
}


function downloadArtifact() {
    if (
        !state.artifactBase64 ||
        !state.artifactMediaType ||
        !state.artifactFilename
    ) {
        return;
    }

    const blob = base64ToBlob(
        state.artifactBase64,
        state.artifactMediaType
    );

    downloadBlob(blob, state.artifactFilename);
}


function downloadCredential() {
    if (!state.credential) {
        return;
    }

    const generationId = (
        state.credential.payload.generation.generation_id
    );

    const credentialJson = JSON.stringify(
        state.credential,
        null,
        2
    );

    const blob = new Blob(
        [credentialJson],
        {
            type: "application/json",
        }
    );

    downloadBlob(
        blob,
        `${generationId}-credential.json`
    );
}


async function copyCredential() {
    if (!state.credential) {
        return;
    }

    const credentialJson = JSON.stringify(
        state.credential,
        null,
        2
    );

    try {
        await navigator.clipboard.writeText(credentialJson);

        const originalText = elements.copyCredentialButton.textContent;

        elements.copyCredentialButton.textContent = "Copied";

        window.setTimeout(
            () => {
                elements.copyCredentialButton.textContent = originalText;
            },
            1400
        );
    } catch {
        setMessage(
            elements.verificationMessage,
            "The browser could not copy the credential automatically.",
            "warning"
        );
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
                ? "Service online"
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

elements.copyCredentialButton.addEventListener(
    "click",
    copyCredential
);

elements.verifyButton.addEventListener(
    "click",
    verifyCredential
);


updatePromptCount();
checkServiceHealth();