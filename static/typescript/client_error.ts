//
//Create a custom error thrower class
export class AIChatError extends Error {
	private error_type: "info" | "warning" | "error";

	constructor(message: string, type: "info" | "warning" | "error" = "error") {
		super(message);
		this.name = "AIChatError";
		this.error_type = type;
		this.flash_message();
	}
	// Create a flash error message that disappears after 5 seconds, and can also be dismissed by clicking on it. Similar to how flask throws its errors, with a red background and white text, and a close button to dismiss the error message.
	private flash_message() {
		// Get the flash section
		const flashSection = <HTMLDivElement | null>(
			document.getElementById("flash_err")
		);
		const errorContainer: HTMLElement | null =
			document.getElementById("err_cont");
		const infoIcons = <HTMLLIElement | null>(
			document.getElementById("info-icons")
		);

		if (!flashSection || !errorContainer || !infoIcons) {
			const dict = {
				flashSection: "Flash Section",
				errorContainer: "Error Container",
				infoIcons: "Info Icons",
			};
			console.assert(
				false,
				`${(!flashSection && dict.flashSection) || (!errorContainer && dict.errorContainer) || (!infoIcons && dict.infoIcons)} not found`,
			);
			return;
		}
		// Clear any existing flash messages but keep the button if it exists
		if (infoIcons.nextElementSibling) {
			infoIcons.nextElementSibling.tagName !== "BUTTON"
				? infoIcons.nextElementSibling.remove()
				: null;
		}
		// Create a new flash message
		this.compile_error_type(errorContainer, infoIcons);
		// Set the error message text
		const errorMessage = document.createElement("span");
		errorMessage.textContent = this.message;
		errorContainer.appendChild(errorMessage);
	}

	private compile_error_type(
		errorContainer: HTMLElement,
		infoIcons: HTMLLIElement,
	) {
		//
		// Based on the error type, set the background color and icon
		switch (this.error_type) {
			case "error":
				errorContainer.classList.add("bg-red-600");
				infoIcons.classList.add("fa-exclamation-triangle");
				break;
			case "warning":
				errorContainer.classList.add("bg-yellow-500", "text-black");
				infoIcons.classList.add("fa-info-circle");
				break;
			case "info":
				errorContainer.classList.add("bg-green-600");
				infoIcons.classList.add("fa-check-circle");
				break;
			default:
				errorContainer.classList.add("bg-green-600");
				infoIcons.classList.add("fa-check-circle");
		}
	}
}
