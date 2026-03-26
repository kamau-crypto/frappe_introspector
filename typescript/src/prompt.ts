import { AIChatError } from "./client_error";

type Provider = "gemini" | "claude" | "chatgpt" | "general" | "qwen";

export function buildContextDeeplinking(provider: Provider): string {
	const current_url = window.location.href;
	const structured_url = encodeURIComponent(current_url);
	switch (provider) {
		case "claude":
			return `https://claude.ai/new?q=Read from this url: -${structured_url} and explain it to me`;
		case "chatgpt":
			return `https://chat.openai.com/?prompt=Read from this url:- ${structured_url} and explain it to me`;
		case "general":
			createMarkdownFormat();
			return "";
		default:
			throw new Error(`Unsupported provider: ${provider}`);
	}
}

export function buildDeepLinkingAction(provider: Provider) {
	const url: string = buildContextDeeplinking(provider);
	url.trim().length > 0 && window.open(url, "_blank");
}

async function createMarkdownFormat(): Promise<string | void> {
	// DocType name & module
	const doctypeName =
		document.querySelector("h2.text-2xl")?.textContent?.trim() ?? "DocType";
	const moduleText =
		document.querySelector("p.text-gray-500")?.textContent?.trim() ?? "";
	const module = moduleText.replace("Module:", "").trim();

	// Field stats — title attributes make these unambiguous
	const stat = (title: string) =>
		document.querySelector(`[title="${title}"]`)?.textContent?.trim() ?? "0";
	const stats = {
		total: stat("Total Fields"),
		required: stat("Required Fields"),
		readonly: stat("Read-only Fields"),
		links: stat("Link Fields"),
	};

	// Optional description
	const descH6 = Array.from(document.querySelectorAll("h6")).find(
		el => el.textContent?.trim() === "Description",
	);
	const description =
		descH6?.parentElement?.querySelector("p")?.textContent?.trim() ?? "";

	// DocType properties from the structured list
	const propertiesEl = document.getElementById("properties_list");
	const propItems = propertiesEl
		? Array.from(propertiesEl.querySelectorAll("li"))
		: [];
	const propertiesMarkdown = propItems
		.map(li => {
			const key = li.querySelector("strong")?.textContent?.trim() ?? "";
			const value = (li.textContent?.trim() ?? "").replace(key, "").trim();
			return `- **${key}** ${value}`;
		})
		.join("\n");

	// Fields table — extract from data attributes + cell content
	const fieldRows = Array.from(
		document.querySelectorAll("#fieldsTableBody .field-row"),
	);
	const fieldLines = fieldRows.map(row => {
		const cells = row.querySelectorAll("td");
		const fieldname = row.getAttribute("data-fieldname") ?? "";
		const label = cells[1]?.textContent?.trim() || "-";
		const type = cells[2]?.textContent?.trim() || "-";
		const options = cells[3]?.textContent?.trim().replace(/\s+/g, " ") || "-";
		const props =
			Array.from(cells[4]?.querySelectorAll("span") ?? [])
				.map(s => s.textContent?.trim())
				.filter(Boolean)
				.join(", ") || "-";
		const defaultVal = cells[5]?.textContent?.trim() || "-";
		return `| \`${fieldname}\` | ${label} | ${type} | ${options} | ${props} | ${defaultVal} |`;
	});

	// Assemble markdown
	const sections: string[] = [
		`# ${doctypeName}`,
		module ? `**Module:** ${module}` : "",
		"",
		"## Summary",
		`- Total Fields: **${stats.total}**`,
		`- Required Fields: **${stats.required}**`,
		`- Read-only Fields: **${stats.readonly}**`,
		`- Link Fields: **${stats.links}**`,
	];

	if (description) {
		sections.push("", "## Description", description);
	}

	sections.push("", "## DocType Properties", propertiesMarkdown);

	if (fieldLines.length > 0) {
		sections.push(
			"",
			`## Fields (${fieldLines.length})`,
			"| Field Name | Label | Type | Options | Properties | Default |",
			"|:-----------|:------|:-----|:--------|:-----------|:--------|",
			...fieldLines,
		);
	}

	const markdown = sections.join("\n");
	return navigator.clipboard.writeText(markdown).finally(() => {
		new AIChatError(
			"Markdown content has been copied to clipboard. Please paste it into your AI assistant.",
		);
	});
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
