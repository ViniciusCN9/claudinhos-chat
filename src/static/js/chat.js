function appendMultilineText(target, content) {
    const lines = String(content).split("\n");
    lines.forEach((line, index) => {
        if (index > 0) {
            target.appendChild(document.createElement("br"));
        }
        target.appendChild(document.createTextNode(line));
    });
}

function createMessageBubble(role, content, extraMeta) {
    const article = document.createElement("article");
    article.className = `message-bubble message-${role}`;

    const meta = document.createElement("div");
    meta.className = "message-meta";

    const timestamp = document.createElement("span");
    timestamp.className = "message-time";
    timestamp.textContent = extraMeta || "agora";

    meta.append(timestamp);

    const body = document.createElement("p");
    appendMultilineText(body, content);

    article.append(meta, body);
    return article;
}

function setError(target, message) {
    if (!target) {
        return;
    }

    if (!message) {
        target.classList.add("hidden");
        target.textContent = "";
        return;
    }

    target.textContent = message;
    target.classList.remove("hidden");
}

function parseJsonScript(id) {
    const node = document.getElementById(id);
    if (!node) {
        return null;
    }

    try {
        return JSON.parse(node.textContent);
    } catch {
        return null;
    }
}

function createSidebarCarousel() {
    const image = document.querySelector("[data-sidebar-carousel-image]");
    const config = parseJsonScript("sidebar-carousel-config");
    const storageKey = "claudinhos-sidebar-carousel-end-until";
    if (!image || !config) {
        return {
            start() {},
            thinking() {},
            end() {},
            resume() {},
        };
    }

    let activeInterval = null;
    let activeTimeout = null;
    let currentIndex = 0;

    const clearTimers = () => {
        if (activeInterval) {
            window.clearInterval(activeInterval);
            activeInterval = null;
        }
        if (activeTimeout) {
            window.clearTimeout(activeTimeout);
            activeTimeout = null;
        }
    };

    const setEndDeadline = (timestamp) => {
        try {
            window.sessionStorage.setItem(storageKey, String(timestamp));
        } catch {
            return;
        }
    };

    const getEndDeadline = () => {
        try {
            const rawValue = window.sessionStorage.getItem(storageKey);
            return rawValue ? Number(rawValue) : 0;
        } catch {
            return 0;
        }
    };

    const clearEndDeadline = () => {
        try {
            window.sessionStorage.removeItem(storageKey);
        } catch {
            return;
        }
    };

    const showFrame = (frames, index) => {
        if (!Array.isArray(frames) || frames.length === 0) {
            return;
        }
        image.src = frames[index % frames.length];
    };

    const startLoop = (frames, delayMs) => {
        clearTimers();
        currentIndex = 0;
        showFrame(frames, currentIndex);
        activeInterval = window.setInterval(() => {
            currentIndex += 1;
            showFrame(frames, currentIndex);
        }, delayMs);
    };

    return {
        start() {
            clearEndDeadline();
            startLoop(config.start, 1000);
        },
        thinking() {
            clearEndDeadline();
            startLoop(config.thinking, 1000);
        },
        end(durationMs = 20000) {
            startLoop(config.end, 1000);
            const deadline = Date.now() + durationMs;
            setEndDeadline(deadline);
            activeTimeout = window.setTimeout(() => {
                this.start();
            }, durationMs);
        },
        resume() {
            const deadline = getEndDeadline();
            if (deadline > Date.now()) {
                this.end(deadline - Date.now());
                return;
            }
            this.start();
        },
    };
}

function setPendingFirstMessage(payload) {
    try {
        window.sessionStorage.setItem("claudinhos-pending-first-message", JSON.stringify(payload));
    } catch {
        return;
    }
}

function getPendingFirstMessage() {
    try {
        const rawValue = window.sessionStorage.getItem("claudinhos-pending-first-message");
        return rawValue ? JSON.parse(rawValue) : null;
    } catch {
        return null;
    }
}

function clearPendingFirstMessage() {
    try {
        window.sessionStorage.removeItem("claudinhos-pending-first-message");
    } catch {
        return;
    }
}

function initCreateConversation(form, carousel) {
    if (!form) {
        return;
    }

    const errorTarget = document.querySelector("[data-create-error]");
    const contentInput = form.querySelector("[name='content']");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setError(errorTarget, "");
        carousel.thinking();

        const submitButton = form.querySelector("button[type='submit']");
        submitButton.disabled = true;

        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: new FormData(form),
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || "Nao foi possivel criar o chat.");
            }
            setPendingFirstMessage({
                conversationId: payload.id,
                content: contentInput?.value.trim() || "",
            });
            window.location.assign(payload.detail_url);
        } catch (error) {
            carousel.end();
            setError(errorTarget, error.message);
        } finally {
            submitButton.disabled = false;
        }
    });
}

function initMessageComposer(form, carousel) {
    if (!form) {
        return;
    }

    const stream = document.querySelector("[data-message-stream]");
    const errorTarget = document.querySelector("[data-chat-error]");
    const textarea = form.querySelector("textarea");
    const submitButton = form.querySelector("button[type='submit']");
    const conversationId = form.dataset.conversationId;

    const submitMessage = async (content, preserveInput = false) => {
        const normalizedContent = content.trim();
        if (!normalizedContent) {
            setError(errorTarget, "Digite uma mensagem antes de enviar.");
            return;
        }

        submitButton.disabled = true;
        if (textarea) {
            textarea.disabled = true;
        }
        carousel.thinking();
        const loadingBubble = createMessageBubble("assistant", "Pensando...", "aguarde");
        loadingBubble.classList.add("message-loading");
        stream.appendChild(createMessageBubble("user", normalizedContent, "agora"));
        stream.appendChild(loadingBubble);
        stream.scrollTop = stream.scrollHeight;

        try {
            const formData = new FormData(form);
            formData.set("content", normalizedContent);

            const response = await fetch(form.action, {
                method: "POST",
                headers: {
                    Accept: "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                },
                body: formData,
            });
            const payload = await response.json();
            if (!response.ok) {
                throw new Error(payload.error || "Erro ao enviar mensagem.");
            }
            loadingBubble.replaceWith(
                createMessageBubble(
                    payload.assistant_message.role,
                    payload.assistant_message.content,
                    payload.assistant_message.model,
                ),
            );
            carousel.end();
            if (!preserveInput) {
                textarea.value = "";
            }
        } catch (error) {
            loadingBubble.remove();
            stream.lastElementChild?.remove();
            carousel.end();
            if (textarea) {
                textarea.value = normalizedContent;
            }
            setError(errorTarget, error.message);
        } finally {
            submitButton.disabled = false;
            if (textarea) {
                textarea.disabled = false;
                textarea.focus();
            }
            stream.scrollTop = stream.scrollHeight;
        }
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        setError(errorTarget, "");

        await submitMessage(textarea.value);
    });

    textarea?.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" || event.ctrlKey || event.isComposing) {
            return;
        }

        event.preventDefault();
        if (!submitButton.disabled) {
            form.requestSubmit();
        }
    });

    const pendingFirstMessage = getPendingFirstMessage();
    if (pendingFirstMessage?.conversationId === conversationId && pendingFirstMessage.content) {
        clearPendingFirstMessage();
        if (textarea) {
            textarea.value = pendingFirstMessage.content;
        }
        submitMessage(pendingFirstMessage.content);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const carousel = createSidebarCarousel();
    const messageForm = document.querySelector("[data-message-form]");
    const pendingFirstMessage = getPendingFirstMessage();
    if (pendingFirstMessage?.conversationId && messageForm?.dataset.conversationId === pendingFirstMessage.conversationId) {
        carousel.thinking();
    } else {
        carousel.resume();
    }
    initCreateConversation(document.querySelector("[data-create-conversation-form]"), carousel);
    initMessageComposer(messageForm, carousel);
});