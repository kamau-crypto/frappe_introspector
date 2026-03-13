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

export function buildContextDeeplinking(
	provider: Provider,
): string {
	const current_url = window.location.href;
	const structured_url = encodeURIComponent(current_url);
	switch (provider) {
		case "claude":
			return `https://claude.ai/new?q=Read from this url: -${structured_url} and explain it to me`;
		case "chatgpt":
			return `https://chat.openai.com/?prompt=Read from this url:- ${structured_url} and explain it to me`;
		default:
			throw new Error(`Unsupported provider: ${provider}`);
	}
}

export function buildDeepLinkingAction(provider: Provider) {
	const url: string = buildContextDeeplinking(provider);
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
