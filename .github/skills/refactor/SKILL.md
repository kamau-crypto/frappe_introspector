---
name: refactor
description: Refactor Javascript into Typescript for templates.
---

To refactor Javascript code into Typescript, you can follow these steps:

1. All the templates are located in the `/templates` directory. Choose one or more of the templates to refactor.
2. In the `/templates/**.html` files, identify the `<script>` tags that contain inline Javascript code. Not links of external Javascript files. Focus on the inline code within the `<script>` tags for refactoring.
3. In the `<script>` tags, identify the Javascript code that performs DOM manipulation, such as selecting elements using methods like:

- `const x= document.querySelector('selector')`
- `const x= document.getElementById('id')`
- `const x= document.getElementsByClassName('class')`

4. For each identified Javascript code, determine the appropriate type annotations based on the context and usage of the variables. For example, if a variable is expected to hold an HTML element, you can use `HTMLElement` as the type annotation. If it is expected to hold a collection of elements, you can use `HTMLCollectionOf<Element>`.
5. In the `/typescript/src/` directory, if any of the above code matches and is tied to DOM manipulation, use `main.ts` to refactor the code into Typescript.
6. For each template, inside the `/templates/**.html` file, create a method inside the `main.ts` file that corresponds to the template. For example, if the template is `template1.html`, create a method called `template1()` in `main.ts`.
7. In some cases, there are `/templates/file.html` files that have a corresponding `/typescript/src/file.ts` file. If you find such a match, still create the method in `main.ts` and refactor the code from the template into that method, even if there is already a corresponding `.ts` file. This will ensure that all the refactored code is centralized in `main.ts` for better organization and maintainability.
8. Each method should contain the refactored Typescript code that corresponds to the identified Javascript code in the template. For example, if you identified a line of Javascript code that selects an element using `document.querySelector`, you can refactor it into Typescript as follows:

```typescript
function template1(): void {
	const x: HTMLElement | null = document.querySelector("selector");
	// Additional refactored code goes here
}
```

9. After refactoring the code, make sure to test the functionality of the templates to ensure that the Typescript code works as expected. You can use a local development server to serve the templates and verify that the DOM manipulation is functioning correctly with the refactored Typescript code.

10. For each function created in `main.ts`, create a test file for unit tests inside the `/typescript/tests` directory. For example, if you created a function called `template1()`, create a test file called `template1.test.ts` in the `/typescript/tests` directory. In this test file, write unit tests to verify the functionality of the refactored code. You can use a testing framework like vitest for testing and running your tests.

11. Repeat the above steps for each template with a `<script>` tag , ensuring that all identified Javascript code is properly refactored into Typescript with appropriate type annotations.

12. Create a report of the refactoring process, including the changes made, the templates that were refactored, and any challenges encountered during the refactoring. Store this report in a file called `/reports/refactor_$(date +%Y-%m-%d)_report.md` in the root directory of the project. This report will serve as documentation for the refactoring process and can be used for future reference.
