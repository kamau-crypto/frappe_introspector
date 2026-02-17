import { AIChatError } from "./client_error.js";

declare const showdown: any;
//
export class Chat {
	private processing_response_flag = false;
	constructor() {
		this.toggle_chat();
		this.chat_message();
		this.setup_clear_history();
	}
	//
	// Toggle the opening and closing of the chat interface.
	private toggle_chat() {
		const chatToggle = <HTMLButtonElement | null>(
			document.getElementById("chat-toggle")
		);
		const chatBody = <HTMLDivElement | null>(
			document.getElementById("chat-body")
		);
		const toggleIcon = <SVGElement | null>(
			document.getElementById("toggle-icon")
		);

		if (!chatToggle || !chatBody || !toggleIcon) {
			const textMsg = () => {
				return (
					(!chatToggle && "Chat Toggle Button") ||
					(!chatBody && "Chat Body") ||
					(!toggleIcon && "Toggle Icon")
				);
			};
			throw new AIChatError(`${textMsg()} not found`);
		}
		// Add click event listener to the toggle button
		chatToggle.addEventListener("click", () => {
			// Check if the chat body is currently hidden
			if (chatBody.style.display === "none") {
				// Show the chat body and rotate the icon
				chatBody.style.display = "flex";
				toggleIcon.classList.remove("rotate-0");
				toggleIcon.classList.add("rotate-180");
			} else {
				// Hide the chat body and reset the icon rotation
				chatBody.style.display = "none";
				toggleIcon.classList.remove("rotate-180");
				toggleIcon.classList.add("rotate-0");
			}
		});
	}

	/**
	 * Setup clear history button functionality
	 */
	private setup_clear_history() {
		const clearHistoryBtn = <HTMLButtonElement | null>(
			document.getElementById("clear-history-btn")
		);

		if (!clearHistoryBtn) {
			console.warn("Clear history button not found");
			return;
		}

		clearHistoryBtn.addEventListener("click", async () => {
			if (confirm("Are you sure you want to clear the conversation history?")) {
				await this.clear_conversation_history();
			}
		});
	}

	/**
	 * Clear conversation history from server and UI
	 */
	private async clear_conversation_history() {
		try {
			const response = await fetch("/clear_history", {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
			});

			if (response.ok) {
				// Clear the chat messages UI
				const chatMessages = <HTMLDivElement | null>(
					document.getElementById("chat_messages")
				);
				if (chatMessages) {
					chatMessages.innerHTML = `
						<div class="mb-4">
							<div class="bg-gray-200 p-3 rounded-lg max-w-xs text-sm text-gray-800">
								Hello! How can I help you today?
							</div>
						</div>
					`;
				}
			} else {
				throw new AIChatError("Failed to clear conversation history");
			}
		} catch (error) {
			console.error("Error clearing history:", error);
			throw new AIChatError("Failed to clear conversation history");
		}
	}

	async chat_message() {
		//
		const chat_form = <HTMLFormElement | null>(
			document.getElementById("chat_form")
		);

		if (!chat_form) {
			throw new AIChatError("Chat form not found");
		}

		chat_form.onsubmit = async e => {
			e.preventDefault();
			//
			if (e && !e.target) {
				throw new AIChatError("Event target not found");
			}
			const message = (e.target as HTMLFormElement).chat.value;
			(e.target as HTMLFormElement).reset();
			try {
				await this.send_request(message);
			} catch (error) {
				console.log("Error sending message:", error);
				throw new AIChatError("Failed to send message");
			}
		};
	}

	async send_request(message: string) {
		const chatMessages = <HTMLDivElement | null>(
			document.getElementById("chat_messages")
		);

		if (!chatMessages) {
			throw new AIChatError("Chat body not found");
		}

		this.user_message(message, chatMessages);
		this.processing_response_flag = true;
		this.processing_response({ chatMessages });

		const response = await fetch("/chat", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify({ message }),
		});
		if (!response.ok) {
			throw new AIChatError("Failed to send message");
		}
		this.processing_response_flag = false;
		this.processing_response({ chatMessages });

		// Create a bot message container for streaming updates
		const botMessageId = this.create_bot_message_container(chatMessages);

		const reader = response.body!.getReader();
		const decoder = new TextDecoder();
		let chunks = "";

		while (true) {
			const { value, done } = await reader.read();
			if (done) break;
			chunks += decoder.decode(value);

			// Update the bot message with new content
			this.update_bot_message(botMessageId, chunks, chatMessages);
		}
	}

	async processing_response({
		chatMessages,
	}: {
		chatMessages: HTMLDivElement;
	}) {
		if (this.processing_response_flag) {
			chatMessages.innerHTML += `<div class="flex justify-start text-sm bg-gray-200 w-fit text-gray-800 p-2 rounded-lg mb-2 w-full animate-pulse">Processing response...</div>`;
			chatMessages.scrollTop = chatMessages.scrollHeight;
		}
		if (!this.processing_response_flag) {
			const processingMsg = chatMessages.querySelector(
				".animate-pulse",
			) as HTMLDivElement | null;
			if (processingMsg) {
				processingMsg.remove();
			}
		}
	}

	/**
	 * Create a bot message container and return its ID for streaming updates
	 */
	private create_bot_message_container(chatMessages: HTMLDivElement): string {
		const botMessageId = `bot-msg-${Date.now()}`;
		const botMessageDiv = document.createElement("div");
		botMessageDiv.id = botMessageId;
		botMessageDiv.className =
			"flex flex-col justify-start text-sm bg-gray-200 w-fit text-gray-800 p-2 rounded-lg mb-2 w-full";
		chatMessages.appendChild(botMessageDiv);
		chatMessages.scrollTop = chatMessages.scrollHeight;
		return botMessageId;
	}

	/**
	 * Update an existing bot message with new content (for streaming)
	 */
	private update_bot_message(
		messageId: string,
		markdownContent: string,
		chatMessages: HTMLDivElement,
	) {
		const messageElement = document.getElementById(messageId);
		if (messageElement) {
			const markdownWithLinks = this.link_to_html({
				markdown: markdownContent,
			});
			const htmlContent = this.render_markdown(markdownWithLinks);
			messageElement.innerHTML = htmlContent;
			chatMessages.scrollTop = chatMessages.scrollHeight;
		}
	}

	/**
	 * Add a complete bot message (for static/non-streaming messages)
	 */
	bot_message(message: string, chatMessages: HTMLDivElement) {
		const htmlContent = this.render_markdown(message);
		const msg = `<div class="flex flex-col justify-start text-sm bg-gray-200 w-fit text-gray-800 p-2 rounded-lg mb-2 w-full">${htmlContent}</div>`;

		chatMessages.innerHTML += msg;
		chatMessages.scrollTop = chatMessages.scrollHeight;
	}

	async user_message(message: string, chatMessages: HTMLDivElement) {
		const msg = `<div class="flex justify-end mb-2">
    <span class="bg-blue-500 text-sm text-white rounded-lg p-3 max-w-[85%]">
    ${message}
    </span>
</div>`;

		chatMessages.innerHTML += msg;
		chatMessages.scrollTop = chatMessages.scrollHeight;
	}

	/**
	 * Render markdown to HTML with links, formatting, code blocks, etc.
	 * Showdown handles: links, bold, italic, code, lists, headers, etc.
	 */
	private render_markdown(markdown: string): string {
		const converter = new showdown.Converter({
			openLinksInNewWindow: true,
			simplifiedAutoLink: true,
			strikethrough: true,
			tables: true,
			tasklists: true,
		});
		return converter.makeHtml(markdown);
	}

	private link_to_html({ markdown: text }: { markdown: string }) {
		const linkRegex = /\[(.+?)\]\((.+?)\)/g;
		const parts = [];

		let lastIndex = 0;
		let match;

		while ((match = linkRegex.exec(text)) !== null) {
			const [fullMatch, linkText, linkUrl] = match;
			const matchStart = match.index;
			const matchEnd = matchStart + fullMatch.length;

			if (lastIndex < matchStart) {
				parts.push(text.slice(lastIndex, matchStart));
			}
			parts.push(
				`<a
				target='_blank'
				rel='noopener noreferrer'
				key="${linkUrl}"
				href="${linkUrl}"
				class='break-words underline offset-2 text-blue-600 visited:text-purple-600 decoration-blue-600 visited:decoration-purple-600'>
				here
			</a>`,
			);
			lastIndex = matchEnd;
		}
		if (lastIndex < text.length) {
			parts.push(text.slice(lastIndex));
		}

		return parts
			.map((part, i) => {
				return part;
			})
			.join("");
	}
}
new Chat();
