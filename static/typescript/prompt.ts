type ChatAction =
	| "explain"
	| "generate_test_data"
	| "convert_typescript"
	| "convert_zod"
	| "convert_sql"
	| "convert_pydantic"
	| "convert_json"
	| "generate_api_docs";

type Provider = "gemini" | "claude" | "chatgpt" | "deepseek" | "qwen";

export function buildPrompt(doctype: object): string {
	const json = JSON.stringify(doctype, null, 2);

	return `The user is working with a doctype in the ERPNext system. To tie down the response and avoid extensive searches restrict your search to the ERPNext documentation avaialable at https://docs.frappe.io/. The user will provide you with some input related to this doctype, and you will respond with one of the following actions based on the user's request:\n\n- "explain": The user wants you to explain the structure and purpose of this doctype in simple terms.\n- "generate_test_data": The user wants you to generate realistic test data for this doctype.\n- "convert_typescript": The user wants you to convert this doctype definition into a TypeScript interface.\n- "convert_zod": The user wants you to convert this doctype definition into a Zod schema.\n- "convert_sql": The user wants you to convert this doctype definition into an SQL table definition.\n- "convert_pydantic" Always ensure that your response is concise and directly addresses the user's request based on the provided doctype definition and any additional context they may have given.`;
}

export function buildContextDeeplinking(
	provider: Provider,
	prompt: string,
): string {
	const current_url = window.location.href;
	const structured_url = encodeURIComponent(current_url);
	switch (provider) {
		case "gemini":
			return `https://gemini.google.com/app/new?prompt=Read from this url:- ${structured_url} and explain it to me`;
		case "claude":
			return `https://claude.ai/new?q=Read from this url: -${structured_url} and explain it to me`;
		case "chatgpt":
			return `https://chat.openai.com/?prompt=Read from this url:- ${structured_url} and explain it to me`;
		case "deepseek":
			return `https://chat.deepseek.com/chat?q=Read from this url:- ${structured_url} and explain it to me`;
		case "qwen":
			return `https://chat.qwen.ai/?q=Read from this url:- ${structured_url} and explain it to me`;
		default:
			throw new Error(`Unsupported provider: ${provider}`);
	}
}

export function buildDeepLinkingAction(provider: Provider) {
	const prompt: string = buildPrompt({});
	const url: string = buildContextDeeplinking(provider, prompt);
	window.open(url, "_blank");
	return url;
}

// Expose for direct calls from non-module inline scripts
(window as any).buildDeepLinkingAction = buildDeepLinkingAction;

function getAndBuild() {
	const selectElement = document.getElementById(
		"aiChatType",
	) as HTMLSelectElement | null;
	if (!selectElement) return;
	selectElement.onchange = () => {
		const provider = selectElement.value as Provider;
		buildDeepLinkingAction(provider);
	};
}

getAndBuild();
