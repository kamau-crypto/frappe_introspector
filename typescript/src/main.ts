/**
 * main.ts — TypeScript refactoring of inline JavaScript from HTML templates.
 *
 * Functions map 1-to-1 to the Jinja2 templates that contained the original
 * inline <script> blocks:
 *   base()           ← base.html    (mobile-menu toggle)
 *   doctypes()       ← doctypes.html (filter / search)
 *   doctype_detail() ← doctype_detail.html (field filter)
 *   openRawDataModal / closeRawDataModal / copyToClipboard / initAiPicker
 *                    ← doctype_detail.html (modal, clipboard, AI picker)
 */

// ─── base.html ────────────────────────────────────────────────────────────────
/**
 * Wires up the mobile hamburger-menu toggle button found in base.html's <nav>.
 */
export function base(): void {
	const btn = document.getElementById(
		"mobile-menu-btn",
	) as HTMLButtonElement | null;
	const menu = document.getElementById("mobile-menu") as HTMLElement | null;
	const icon = document.getElementById("hamburger-icon") as HTMLElement | null;

	if (!btn || !menu || !icon) return;

	btn.addEventListener("click", function () {
		const isOpen = !menu.classList.contains("hidden");
		menu.classList.toggle("hidden", isOpen);
		icon.classList.toggle("fa-bars", isOpen);
		icon.classList.toggle("fa-times", !isOpen);
		btn.setAttribute("aria-expanded", String(!isOpen));
	});
}

// ─── doctypes.html ────────────────────────────────────────────────────────────
/**
 * Initialises the DocType grid filter/search controls on doctypes.html.
 * Deduplicates the module <select> options and wires up all four controls.
 * Also applies the `?module=` URL query param deep-link from the homepage.
 */
export function doctypes(): void {
	const searchInput = document.getElementById(
		"searchDocTypes",
	) as HTMLInputElement | null;
	const moduleFilter = document.getElementById(
		"moduleFilter",
	) as HTMLSelectElement | null;
	const typeFilter = document.getElementById(
		"typeFilter",
	) as HTMLSelectElement | null;
	const clearButton = document.getElementById(
		"clearFilters",
	) as HTMLButtonElement | null;
	const doctypeItems = document.querySelectorAll<HTMLElement>(".doctype-item");
	const noResults = document.getElementById("noResults") as HTMLElement | null;

	if (
		!searchInput ||
		!moduleFilter ||
		!typeFilter ||
		!clearButton ||
		!noResults
	)
		return;

	// Remove duplicate options from the module filter
	const uniqueModules = new Set<string>();
	Array.from(moduleFilter.options).forEach(option => {
		if (option.value && uniqueModules.has(option.value)) {
			option.remove();
		} else if (option.value) {
			uniqueModules.add(option.value);
		}
	});

	function filterDocTypes(): void {
		const searchTerm = searchInput!.value.toLowerCase();
		const selectedModule = moduleFilter!.value;
		const selectedType = typeFilter!.value;
		let visibleCount = 0;

		doctypeItems.forEach(item => {
			const itemName = item.dataset.name ?? "";
			const itemModule = item.dataset.module ?? "";
			const itemType = item.dataset.type ?? "";

			const matchesSearch = itemName.includes(searchTerm);
			const matchesModule = !selectedModule || itemModule === selectedModule;
			const matchesType = !selectedType || itemType === selectedType;

			if (matchesSearch && matchesModule && matchesType) {
				item.style.display = "";
				visibleCount++;
			} else {
				item.style.display = "none";
			}
		});

		noResults!.classList.toggle("hidden", visibleCount > 0);
	}

	function clearFilters(): void {
		searchInput!.value = "";
		moduleFilter!.value = "";
		typeFilter!.value = "";
		filterDocTypes();
	}

	searchInput.addEventListener("input", filterDocTypes);
	moduleFilter.addEventListener("change", filterDocTypes);
	typeFilter.addEventListener("change", filterDocTypes);
	clearButton.addEventListener("click", clearFilters);

	// Apply ?module= query param from homepage deep-links
	const urlParams = new URLSearchParams(window.location.search);
	const moduleParam = urlParams.get("module");
	if (moduleParam) {
		const matchingOption = Array.from(moduleFilter.options).find(
			o => o.value === moduleParam,
		);
		if (matchingOption) {
			moduleFilter.value = moduleParam;
			filterDocTypes();
		}
	}
}

// ─── doctype_detail.html — field table filter ─────────────────────────────────
/**
 * Wires up the fields-table filter controls on doctype_detail.html.
 */
export function doctype_detail(): void {
	const fieldSearch = document.getElementById(
		"fieldSearch",
	) as HTMLInputElement | null;
	const fieldTypeFilter = document.getElementById(
		"fieldTypeFilter",
	) as HTMLSelectElement | null;
	const requiredFilter = document.getElementById(
		"requiredFilter",
	) as HTMLSelectElement | null;
	const readOnlyFilter = document.getElementById(
		"readOnlyFilter",
	) as HTMLSelectElement | null;
	const clearFiltersBtn = document.getElementById(
		"clearFieldFilters",
	) as HTMLButtonElement | null;
	const fieldRows =
		document.querySelectorAll<HTMLTableRowElement>(".field-row");

	if (
		!fieldSearch ||
		!fieldTypeFilter ||
		!requiredFilter ||
		!readOnlyFilter ||
		!clearFiltersBtn
	)
		return;

	function filterFields(): void {
		const searchTerm = fieldSearch!.value.toLowerCase();
		const selectedType = fieldTypeFilter!.value;
		const selectedRequired = requiredFilter!.value;
		const selectedReadOnly = readOnlyFilter!.value;

		fieldRows.forEach(row => {
			const fieldname = row.dataset.fieldname ?? "";
			const label = row.dataset.label ?? "";
			const fieldtype = row.dataset.fieldtype ?? "";
			const required = row.dataset.required === "true";
			const readonly = row.dataset.readonly === "true";

			const matchesSearch =
				fieldname.includes(searchTerm) || label.includes(searchTerm);
			const matchesType = !selectedType || fieldtype === selectedType;
			const matchesRequired =
				!selectedRequired ||
				(selectedRequired === "required" && required) ||
				(selectedRequired === "optional" && !required);
			const matchesReadOnly =
				!selectedReadOnly ||
				(selectedReadOnly === "readonly" && readonly) ||
				(selectedReadOnly === "editable" && !readonly);

			if (matchesSearch && matchesType && matchesRequired && matchesReadOnly) {
				row.style.display = "";
			} else {
				row.style.display = "none";
			}
		});
	}

	function clearFieldFilters(): void {
		fieldSearch!.value = "";
		fieldTypeFilter!.value = "";
		requiredFilter!.value = "";
		readOnlyFilter!.value = "";
		filterFields();
	}

	fieldSearch.addEventListener("input", filterFields);
	fieldTypeFilter.addEventListener("change", filterFields);
	requiredFilter.addEventListener("change", filterFields);
	readOnlyFilter.addEventListener("change", filterFields);
	clearFiltersBtn.addEventListener("click", clearFieldFilters);
}

// ─── doctype_detail.html — Raw Data Modal ─────────────────────────────────────
/**
 * Opens the Raw Data modal and triggers syntax highlighting if Prism is loaded.
 * Exposed globally so inline `onclick="openRawDataModal()"` handlers work.
 */
export function openRawDataModal(): void {
	const modal = document.getElementById("rawDataModal") as HTMLElement | null;
	if (!modal) return;
	modal.classList.remove("hidden");
	modal.classList.add("opacity-100");
	const w = window as Window & { Prism?: { highlightAll: () => void } };
	w.Prism?.highlightAll();
}

/**
 * Closes the Raw Data modal.
 * Exposed globally so inline `onclick="closeRawDataModal()"` handlers work.
 */
export function closeRawDataModal(): void {
	const modal = document.getElementById("rawDataModal") as HTMLElement | null;
	if (!modal) return;
	modal.classList.add("hidden");
	modal.classList.remove("opacity-100");
}

// ─── doctype_detail.html — Clipboard copy ─────────────────────────────────────
/**
 * Copies the text content of `elementId` to the clipboard and briefly shows
 * the #clipboardPopup notification.
 * Exposed globally so inline `onclick="copyToClipboard('rawJsonData')"` works.
 */
export function copyToClipboard(elementId: string): void {
	const element = document.getElementById(elementId) as HTMLElement | null;
	if (!element) return;
	const text = element.textContent ?? "";

	void navigator.clipboard.writeText(text).then(() => {
		const popup = document.getElementById(
			"clipboardPopup",
		) as HTMLElement | null;
		if (!popup) return;
		popup.classList.remove("hidden");
		setTimeout(() => {
			popup.classList.add("hidden");
		}, 2000);
	});
}

// ─── doctype_detail.html — AI Picker dropdown ────────────────────────────────
/**
 * Initialises the AI-provider selector dropdown identified by `wrapperId`.
 * Updates the trigger button display and fires either a clipboard copy or an
 * AI deep-link action (`window.buildDeepLinkingAction`) on item selection.
 */
export function initAiPicker(wrapperId: string): void {
	const wrapper = document.getElementById(wrapperId) as HTMLElement | null;
	if (!wrapper) return;

	const btn = document.getElementById(
		"aiPickerBtn",
	) as HTMLButtonElement | null;
	const menu = document.getElementById("aiPickerMenu") as HTMLElement | null;
	const chevron = document.getElementById(
		"aiPickerChevron",
	) as HTMLElement | null;

	if (!btn || !menu || !chevron) return;

	function openMenu(): void {
		menu!.classList.remove("hidden");
		chevron!.style.transform = "rotate(180deg)";
		btn!.setAttribute("aria-expanded", "true");
	}

	function closeMenu(): void {
		menu!.classList.add("hidden");
		chevron!.style.transform = "";
		btn!.setAttribute("aria-expanded", "false");
	}

	btn.addEventListener("click", (e: MouseEvent) => {
		e.stopPropagation();
		menu!.classList.contains("hidden") ? openMenu() : closeMenu();
	});

	wrapper.querySelectorAll<HTMLElement>(".ai-pick").forEach(item => {
		item.addEventListener("click", function (this: HTMLElement) {
			const val = this.dataset.ai;

			const iconEl = this.querySelector("img, i");
			const aiPickerIcon = document.getElementById("aiPickerIcon");
			const aiPickerLabel = document.getElementById("aiPickerLabel");

			if (aiPickerIcon && iconEl) {
				aiPickerIcon.innerHTML = iconEl.outerHTML;
			}
			if (aiPickerLabel) {
				const firstSpan = this.querySelector("span");
				aiPickerLabel.textContent = firstSpan?.textContent?.trim() ?? "";
			}

			wrapper
				.querySelectorAll<HTMLElement>(".ai-pick")
				.forEach(i => i.classList.remove("font-semibold"));
			this.classList.add("font-semibold");
			this.setAttribute("aria-selected", "true");
			closeMenu();

			if (val === "general") {
				const code = document.getElementById(
					"rawJsonData",
				) as HTMLElement | null;
				if (code) {
					void navigator.clipboard
						.writeText(code.textContent ?? "")
						.then(() => {
							const popup = document.getElementById(
								"clipboardPopup",
							) as HTMLElement | null;
							if (!popup) return;
							popup.classList.remove("hidden");
							setTimeout(() => popup.classList.add("hidden"), 2000);
						});
				}
			} else if (val) {
				const w = window as Window & {
					buildDeepLinkingAction?: (v: string) => void;
				};
				w.buildDeepLinkingAction?.(val);
			}
		});
	});

	// Close when clicking outside the wrapper
	document.addEventListener("click", (e: MouseEvent) => {
		if (!wrapper.contains(e.target as Node)) closeMenu();
	});
}

// ─── Expose globals for inline onclick handlers ──────────────────────────────
type ExtendedWindow = Window & {
	openRawDataModal: () => void;
	closeRawDataModal: () => void;
	copyToClipboard: (id: string) => void;
	initAiPicker: (id: string) => void;
};
(window as unknown as ExtendedWindow).openRawDataModal = openRawDataModal;
(window as unknown as ExtendedWindow).closeRawDataModal = closeRawDataModal;
(window as unknown as ExtendedWindow).copyToClipboard = copyToClipboard;
(window as unknown as ExtendedWindow).initAiPicker = initAiPicker;

// ─── Auto-initialise on module load ──────────────────────────────────────────
// Module scripts are deferred — the DOM is ready when this runs.
base();
doctypes();
doctype_detail();
initAiPicker("aiPickerWrapper");
