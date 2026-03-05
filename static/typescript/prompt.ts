type ChatAction =
	| "explain"
	| "generate_test_data"
	| "convert_typescript"
	| "convert_zod"
	| "convert_sql"
	| "convert_pydantic"
	| "convert_json"
	| "generate_api_docs";

type Provider = "gemini" | "claude" | "chatgpt" | "DeepSeek" | "Qwen";

export function buildPrompt(doctype: object): string {
	const json = JSON.stringify(doctype, null, 2);

	return `The user is working with a doctype in the ERPNext system. To tie down the response and avoid extensive searches restrict your search to the ERPNext documentation avaialable at https://docs.frappe.io/. The doctype is defined as follows:\n\n${json}\n\nThe user will provide you with some input related to this doctype, and you will respond with one of the following actions based on the user's request:\n\n- "explain": The user wants you to explain the structure and purpose of this doctype in simple terms.\n- "generate_test_data": The user wants you to generate realistic test data for this doctype.\n- "convert_typescript": The user wants you to convert this doctype definition into a TypeScript interface.\n- "convert_zod": The user wants you to convert this doctype definition into a Zod schema.\n- "convert_sql": The user wants you to convert this doctype definition into an SQL table definition.\n- "convert_pydantic": The user wants you to convert this doctype definition into a Pydantic model.\n- "convert_json": The user wants you to convert this doctype definition into a JSON Schema.\n- "generate_api_docs": The user wants you to generate API documentation for this doctype. The user can Also provide you with extra context to help you generate a more accurate response. Always ensure that your response is concise and directly addresses the user's request based on the provided doctype definition and any additional context they may have given.`;
}

export function buildContextDeeplinking(
	provider: Provider,
	prompt: string,
): string {
	switch (provider) {
		case "gemini":
			return `https://gemini.google.com/app/new?q=${encodeURIComponent(prompt)}`;
		case "claude":
			return `https://claude.ai/chat?input=${encodeURIComponent(prompt)}`;
		case "chatgpt":
			return `https://chat.openai.com/chat?input=${encodeURIComponent(prompt)}`;
		case "DeepSeek":
			return `https://deepseek.ai/?q=${encodeURIComponent(prompt)}`;
		case "Qwen":
			return `https://qwen.qq.com/?q=${encodeURIComponent(prompt)}`;
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
