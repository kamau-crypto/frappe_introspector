/**
 * Tests for functions extracted from doctype_detail.html:
 *   - doctype_detail()   — field-table filtering
 *   - openRawDataModal() / closeRawDataModal() — modal toggle
 *   - copyToClipboard()  — clipboard + popup notification
 *   - initAiPicker()     — AI provider dropdown
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
	closeRawDataModal,
	copyToClipboard,
	doctype_detail,
	initAiPicker,
	openRawDataModal,
} from "../src/main";

// ─── doctype_detail() ─────────────────────────────────────────────────────────

function buildFieldFilterDOM(): void {
	document.body.innerHTML = `
    <input id="fieldSearch" type="text" value="" />
    <select id="fieldTypeFilter">
      <option value="">All</option>
      <option value="Data">Data</option>
      <option value="Link">Link</option>
    </select>
    <select id="requiredFilter">
      <option value="">All</option>
      <option value="required">Required</option>
      <option value="optional">Optional</option>
    </select>
    <select id="readOnlyFilter">
      <option value="">All</option>
      <option value="readonly">Read-only</option>
      <option value="editable">Editable</option>
    </select>
    <button id="clearFieldFilters">Clear</button>

    <table>
      <tbody id="fieldsTableBody">
        <tr class="field-row" data-fieldname="name" data-label="Full Name"
            data-fieldtype="Data" data-required="true" data-readonly="false"></tr>
        <tr class="field-row" data-fieldname="company" data-label="Company"
            data-fieldtype="Link" data-required="false" data-readonly="true"></tr>
        <tr class="field-row" data-fieldname="status" data-label="Status"
            data-fieldtype="Data" data-required="false" data-readonly="false"></tr>
      </tbody>
    </table>
  `;
}

describe("doctype_detail() — field table filter", () => {
	beforeEach(() => buildFieldFilterDOM());

	it("does nothing when required elements are absent", () => {
		document.body.innerHTML = "";
		expect(() => doctype_detail()).not.toThrow();
	});

	it("hides rows not matching the search term (fieldname)", () => {
		doctype_detail();
		const input = document.getElementById("fieldSearch") as HTMLInputElement;
		input.value = "name";
		input.dispatchEvent(new Event("input"));

		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		expect(rows[0].style.display).toBe(""); // name — matches
		expect(rows[1].style.display).toBe("none");
		expect(rows[2].style.display).toBe("none");
	});

	it("matches by label text", () => {
		doctype_detail();
		const input = document.getElementById("fieldSearch") as HTMLInputElement;
		input.value = "company";
		input.dispatchEvent(new Event("input"));

		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		expect(rows[1].style.display).toBe(""); // Company label matches
	});

	it("filters by field type", () => {
		doctype_detail();
		const typeFilter = document.getElementById(
			"fieldTypeFilter",
		) as HTMLSelectElement;
		typeFilter.value = "Link";
		typeFilter.dispatchEvent(new Event("change"));

		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		expect(rows[0].style.display).toBe("none"); // Data
		expect(rows[1].style.display).toBe(""); // Link
		expect(rows[2].style.display).toBe("none"); // Data
	});

	it("filters required fields only", () => {
		doctype_detail();
		const reqFilter = document.getElementById(
			"requiredFilter",
		) as HTMLSelectElement;
		reqFilter.value = "required";
		reqFilter.dispatchEvent(new Event("change"));

		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		expect(rows[0].style.display).toBe(""); // required=true
		expect(rows[1].style.display).toBe("none");
		expect(rows[2].style.display).toBe("none");
	});

	it("filters optional (non-required) fields", () => {
		doctype_detail();
		const reqFilter = document.getElementById(
			"requiredFilter",
		) as HTMLSelectElement;
		reqFilter.value = "optional";
		reqFilter.dispatchEvent(new Event("change"));

		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		expect(rows[0].style.display).toBe("none");
		expect(rows[1].style.display).toBe(""); // required=false
		expect(rows[2].style.display).toBe(""); // required=false
	});

	it("filters read-only fields", () => {
		doctype_detail();
		const roFilter = document.getElementById(
			"readOnlyFilter",
		) as HTMLSelectElement;
		roFilter.value = "readonly";
		roFilter.dispatchEvent(new Event("change"));

		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		expect(rows[0].style.display).toBe("none");
		expect(rows[1].style.display).toBe(""); // readonly=true
		expect(rows[2].style.display).toBe("none");
	});

	it("clear button resets all filters", () => {
		doctype_detail();
		const input = document.getElementById("fieldSearch") as HTMLInputElement;
		input.value = "name";
		input.dispatchEvent(new Event("input"));

		const clearBtn = document.getElementById(
			"clearFieldFilters",
		) as HTMLButtonElement;
		clearBtn.click();

		expect(input.value).toBe("");
		const rows = document.querySelectorAll<HTMLTableRowElement>(".field-row");
		rows.forEach(r => expect(r.style.display).toBe(""));
	});
});

// ─── openRawDataModal() / closeRawDataModal() ─────────────────────────────────

function buildModalDOM(): void {
	document.body.innerHTML = `<div id="rawDataModal" class="hidden"></div>`;
}

describe("openRawDataModal() / closeRawDataModal()", () => {
	beforeEach(() => buildModalDOM());

	it("openRawDataModal removes hidden and adds opacity-100", () => {
		openRawDataModal();
		const modal = document.getElementById("rawDataModal") as HTMLElement;
		expect(modal.classList.contains("hidden")).toBe(false);
		expect(modal.classList.contains("opacity-100")).toBe(true);
	});

	it("closeRawDataModal adds hidden and removes opacity-100", () => {
		openRawDataModal();
		closeRawDataModal();
		const modal = document.getElementById("rawDataModal") as HTMLElement;
		expect(modal.classList.contains("hidden")).toBe(true);
		expect(modal.classList.contains("opacity-100")).toBe(false);
	});

	it("does nothing when modal element is absent", () => {
		document.body.innerHTML = "";
		expect(() => openRawDataModal()).not.toThrow();
		expect(() => closeRawDataModal()).not.toThrow();
	});
});

// ─── copyToClipboard() ────────────────────────────────────────────────────────

describe("copyToClipboard()", () => {
	beforeEach(() => {
		document.body.innerHTML = `
      <code id="rawJsonData">{"name":"Account"}</code>
      <div id="clipboardPopup" class="hidden"></div>
    `;
		// Mock the clipboard API
		Object.defineProperty(navigator, "clipboard", {
			value: { writeText: vi.fn().mockResolvedValue(undefined) },
			writable: true,
		});
	});

	it("calls navigator.clipboard.writeText with element text", async () => {
		copyToClipboard("rawJsonData");
		await Promise.resolve(); // flush microtask
		expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
			'{"name":"Account"}',
		);
	});

	it("shows the popup notification after copy", async () => {
		copyToClipboard("rawJsonData");
		await new Promise(r => setTimeout(r, 0)); // flush promise
		const popup = document.getElementById("clipboardPopup") as HTMLElement;
		expect(popup.classList.contains("hidden")).toBe(false);
	});

	it("does nothing when element is not found", () => {
		expect(() => copyToClipboard("nonexistent")).not.toThrow();
		expect(navigator.clipboard.writeText).not.toHaveBeenCalled();
	});
});

// ─── initAiPicker() ──────────────────────────────────────────────────────────

function buildAiPickerDOM(): void {
	document.body.innerHTML = `
    <div id="aiPickerWrapper">
      <button id="aiPickerBtn" aria-expanded="false">
        <span id="aiPickerIcon"><i class="fas fa-clipboard"></i></span>
        <span id="aiPickerLabel">Copy from this page</span>
        <i id="aiPickerChevron" class="fas fa-chevron-down"></i>
      </button>
      <div id="aiPickerMenu" class="hidden">
        <button class="ai-pick" data-ai="general">
          <i class="fas fa-clipboard"></i>
          <span>Copy<span>Copy page data to clipboard</span></span>
        </button>
        <button class="ai-pick" data-ai="claude">
          <img src="claude.png" alt="" />
          <span>Claude<span>Ask questions</span></span>
        </button>
      </div>
    </div>
    <code id="rawJsonData">{"test":1}</code>
    <div id="clipboardPopup" class="hidden"></div>
  `;
	Object.defineProperty(navigator, "clipboard", {
		value: { writeText: vi.fn().mockResolvedValue(undefined) },
		writable: true,
	});
}

describe("initAiPicker()", () => {
	beforeEach(() => buildAiPickerDOM());

	it("does nothing when wrapper is absent", () => {
		document.body.innerHTML = "";
		expect(() => initAiPicker("aiPickerWrapper")).not.toThrow();
	});

	it("opens the menu when the trigger button is clicked", () => {
		initAiPicker("aiPickerWrapper");
		const btn = document.getElementById("aiPickerBtn") as HTMLButtonElement;
		btn.click();
		const menu = document.getElementById("aiPickerMenu") as HTMLElement;
		expect(menu.classList.contains("hidden")).toBe(false);
		expect(btn.getAttribute("aria-expanded")).toBe("true");
	});

	it("closes the menu on second trigger-button click", () => {
		initAiPicker("aiPickerWrapper");
		const btn = document.getElementById("aiPickerBtn") as HTMLButtonElement;
		btn.click(); // open
		btn.click(); // close
		const menu = document.getElementById("aiPickerMenu") as HTMLElement;
		expect(menu.classList.contains("hidden")).toBe(true);
		expect(btn.getAttribute("aria-expanded")).toBe("false");
	});

	it("closes the menu when clicking outside the wrapper", () => {
		initAiPicker("aiPickerWrapper");
		const btn = document.getElementById("aiPickerBtn") as HTMLButtonElement;
		btn.click(); // open

		document.body.dispatchEvent(new MouseEvent("click", { bubbles: true }));
		const menu = document.getElementById("aiPickerMenu") as HTMLElement;
		expect(menu.classList.contains("hidden")).toBe(true);
	});

	it("clicking 'general' ai-pick calls clipboard.writeText", async () => {
		initAiPicker("aiPickerWrapper");
		const btn = document.getElementById("aiPickerBtn") as HTMLButtonElement;
		btn.click(); // open menu

		const generalPick = document.querySelector<HTMLElement>(
			'.ai-pick[data-ai="general"]',
		)!;
		generalPick.click();

		await new Promise(r => setTimeout(r, 0));
		expect(navigator.clipboard.writeText).toHaveBeenCalledWith('{"test":1}');
	});

	it("clicking an ai-pick item marks it as active", () => {
		initAiPicker("aiPickerWrapper");
		const btn = document.getElementById("aiPickerBtn") as HTMLButtonElement;
		btn.click();

		const generalPick = document.querySelector<HTMLElement>(
			'.ai-pick[data-ai="general"]',
		)!;
		generalPick.click();

		expect(generalPick.classList.contains("font-semibold")).toBe(true);
		expect(generalPick.getAttribute("aria-selected")).toBe("true");
	});

	it("clicking a non-general ai-pick calls buildDeepLinkingAction", () => {
		const mockAction = vi.fn();
		(window as unknown as Record<string, unknown>).buildDeepLinkingAction =
			mockAction;

		initAiPicker("aiPickerWrapper");
		const btn = document.getElementById("aiPickerBtn") as HTMLButtonElement;
		btn.click();

		const claudePick = document.querySelector<HTMLElement>(
			'.ai-pick[data-ai="claude"]',
		)!;
		claudePick.click();

		expect(mockAction).toHaveBeenCalledWith("claude");
	});
});
