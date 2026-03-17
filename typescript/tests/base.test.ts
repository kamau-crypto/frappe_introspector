/**
 * Tests for the `base()` function extracted from base.html (mobile-menu toggle).
 */
import { beforeEach, describe, expect, it } from "vitest";
import { base } from "../src/main";

function buildBaseDOM(): void {
	document.body.innerHTML = `
    <button id="mobile-menu-btn" aria-expanded="false">
      <i id="hamburger-icon" class="fas fa-bars"></i>
    </button>
    <div id="mobile-menu" class="hidden"></div>
  `;
}

describe("base() — mobile menu toggle", () => {
	beforeEach(() => {
		buildBaseDOM();
	});

	it("does nothing when required elements are absent", () => {
		document.body.innerHTML = "";
		expect(() => base()).not.toThrow();
	});

	it("opens the menu on first click", () => {
		base();
		const btn = document.getElementById("mobile-menu-btn") as HTMLButtonElement;
		const menu = document.getElementById("mobile-menu") as HTMLElement;
		const icon = document.getElementById("hamburger-icon") as HTMLElement;

		btn.click();

		expect(menu.classList.contains("hidden")).toBe(false);
		expect(icon.classList.contains("fa-times")).toBe(true);
		expect(icon.classList.contains("fa-bars")).toBe(false);
		expect(btn.getAttribute("aria-expanded")).toBe("true");
	});

	it("closes the menu on second click", () => {
		base();
		const btn = document.getElementById("mobile-menu-btn") as HTMLButtonElement;
		const menu = document.getElementById("mobile-menu") as HTMLElement;

		btn.click(); // open
		btn.click(); // close

		expect(menu.classList.contains("hidden")).toBe(true);
		expect(btn.getAttribute("aria-expanded")).toBe("false");
	});

	it("toggles the hamburger icon classes correctly on each click", () => {
		base();
		const btn = document.getElementById("mobile-menu-btn") as HTMLButtonElement;
		const icon = document.getElementById("hamburger-icon") as HTMLElement;

		btn.click();
		expect(icon.classList.contains("fa-times")).toBe(true);
		expect(icon.classList.contains("fa-bars")).toBe(false);

		btn.click();
		expect(icon.classList.contains("fa-bars")).toBe(true);
		expect(icon.classList.contains("fa-times")).toBe(false);
	});
});
