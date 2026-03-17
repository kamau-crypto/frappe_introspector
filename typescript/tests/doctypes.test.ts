/**
 * Tests for the `doctypes()` function extracted from doctypes.html.
 * Covers: deduplication, text-search filter, module filter, type filter,
 * clear-filters, and the `?module=` URL deep-link.
 */
import { beforeEach, describe, expect, it } from "vitest";
import { doctypes } from "../src/main";

function buildDoctypesDOM(): void {
	document.body.innerHTML = `
    <input id="searchDocTypes" type="text" value="" />
    <select id="moduleFilter">
      <option value="">All Modules</option>
      <option value="Accounts">Accounts</option>
      <option value="Accounts">Accounts</option>
      <option value="Stock">Stock</option>
    </select>
    <select id="typeFilter">
      <option value="">All Types</option>
      <option value="standard">Standard</option>
      <option value="custom">Custom</option>
    </select>
    <button id="clearFilters">Clear</button>

    <div id="doctypesGrid">
      <div class="doctype-item" data-name="account" data-module="Accounts" data-type="standard"></div>
      <div class="doctype-item" data-name="sales order" data-module="Selling" data-type="standard"></div>
      <div class="doctype-item" data-name="custom item" data-module="Stock" data-type="custom"></div>
    </div>

    <div id="noResults" class="hidden"></div>
  `;
}

describe("doctypes() — filter / search", () => {
	beforeEach(() => {
		buildDoctypesDOM();
		// Reset location search so URL param tests start clean
		Object.defineProperty(window, "location", {
			writable: true,
			value: { search: "", href: "http://localhost/" },
		});
	});

	it("does nothing when required elements are absent", () => {
		document.body.innerHTML = "";
		expect(() => doctypes()).not.toThrow();
	});

	it("deduplicates module filter options", () => {
		doctypes();
		const moduleFilter = document.getElementById(
			"moduleFilter",
		) as HTMLSelectElement;
		const accountsOptions = Array.from(moduleFilter.options).filter(
			o => o.value === "Accounts",
		);
		expect(accountsOptions).toHaveLength(1);
	});

	it("hides items not matching the search term", () => {
		doctypes();
		const searchInput = document.getElementById(
			"searchDocTypes",
		) as HTMLInputElement;
		searchInput.value = "account";
		searchInput.dispatchEvent(new Event("input"));

		const items = document.querySelectorAll<HTMLElement>(".doctype-item");
		expect(items[0].style.display).toBe(""); // account — visible
		expect(items[1].style.display).toBe("none"); // sales order — hidden
		expect(items[2].style.display).toBe("none"); // custom item — hidden
	});

	it("shows noResults banner when nothing matches", () => {
		doctypes();
		const searchInput = document.getElementById(
			"searchDocTypes",
		) as HTMLInputElement;
		const noResults = document.getElementById("noResults") as HTMLElement;

		searchInput.value = "zzzzz";
		searchInput.dispatchEvent(new Event("input"));

		expect(noResults.classList.contains("hidden")).toBe(false);
	});

	it("filters by module", () => {
		doctypes();
		const moduleFilter = document.getElementById(
			"moduleFilter",
		) as HTMLSelectElement;
		moduleFilter.value = "Accounts";
		moduleFilter.dispatchEvent(new Event("change"));

		const items = document.querySelectorAll<HTMLElement>(".doctype-item");
		expect(items[0].style.display).toBe(""); // Accounts — visible
		expect(items[1].style.display).toBe("none"); // Selling — hidden
		expect(items[2].style.display).toBe("none"); // Stock — hidden
	});

	it("filters by type", () => {
		doctypes();
		const typeFilter = document.getElementById(
			"typeFilter",
		) as HTMLSelectElement;
		typeFilter.value = "custom";
		typeFilter.dispatchEvent(new Event("change"));

		const items = document.querySelectorAll<HTMLElement>(".doctype-item");
		expect(items[0].style.display).toBe("none");
		expect(items[1].style.display).toBe("none");
		expect(items[2].style.display).toBe(""); // custom only
	});

	it("clear button resets all filters and shows all items", () => {
		doctypes();
		const searchInput = document.getElementById(
			"searchDocTypes",
		) as HTMLInputElement;
		const moduleFilter = document.getElementById(
			"moduleFilter",
		) as HTMLSelectElement;
		const clearButton = document.getElementById(
			"clearFilters",
		) as HTMLButtonElement;

		searchInput.value = "account";
		searchInput.dispatchEvent(new Event("input"));
		moduleFilter.value = "Accounts";
		moduleFilter.dispatchEvent(new Event("change"));

		clearButton.click();

		expect(searchInput.value).toBe("");
		expect(moduleFilter.value).toBe("");
		const items = document.querySelectorAll<HTMLElement>(".doctype-item");
		items.forEach(item => expect(item.style.display).toBe(""));
	});

	it("applies ?module= URL param deep-link", () => {
		Object.defineProperty(window, "location", {
			writable: true,
			value: { search: "?module=Stock", href: "http://localhost/" },
		});
		doctypes();

		const moduleFilter = document.getElementById(
			"moduleFilter",
		) as HTMLSelectElement;
		expect(moduleFilter.value).toBe("Stock");

		const items = document.querySelectorAll<HTMLElement>(".doctype-item");
		expect(items[2].style.display).toBe(""); // Stock/custom item visible
		expect(items[0].style.display).toBe("none"); // Accounts hidden
	});
});
