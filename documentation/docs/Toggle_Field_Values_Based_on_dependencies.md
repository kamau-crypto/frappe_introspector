# ERPNext: Toggling Field Values Based on Dependencies

**Date:** 2025-10-29

## Overview

In ERPNext, you can dynamically toggle the visibility or value of a field based on another field’s selected value. This feature allows you to create interactive forms that respond to user input without needing to write complex client scripts.

This behavior can be achieved using the **"Depends On"** field in **Doctype customization** or when defining a new **custom field**.

---

## Step-by-Step Guide

### 1. Navigate to Customize Form

1. Go to **Settings → Customize Form**.
2. Select the **Doctype** you want to customize (e.g., *Sales Invoice*, *Purchase Order*, etc.).
3. Locate or add the field you want to make dependent.

---

### 2. Define the Dependency Rule

In the **Depends On** field, provide a JavaScript-style expression that evaluates to a boolean.

For example:

```text
eval:doc.field_name === "dependent_field_value"
```

### Explanation:

- `eval:` → This prefix tells ERPNext to evaluate the following expression as JavaScript.
- `doc.field_name` → Refers to the value of the field you’re depending on.
- `===` → Ensures a strict comparison between the field value and the expected value.
- `"dependent_field_value"` → Replace this with the value that should trigger the dependent field.

When the expression evaluates to `true`, the field will be **shown** or **enabled**; otherwise, it will remain hidden or disabled.

---

### 3. Example Use Case

Let’s say you have a **Customer Type** field and a **Credit Limit** field.

You only want **Credit Limit** to appear if **Customer Type** equals `"Credit"`.

In the **Depends On** field for *Credit Limit*, you’d enter:

```text
eval:doc.customer_type === "Credit"
```

Now, when you select **Customer Type → Credit**, the **Credit Limit** field appears automatically.

---

### 4. Using Multiple Conditions

You can also use logical operators to combine multiple conditions:

```text
eval:doc.customer_type === "Credit" && doc.region === "Domestic"
```

This means the dependent field will only appear if **Customer Type = Credit** *and* **Region = Domestic**.

---

### 5. Alternative: Using Custom Scripts

If you need more advanced behavior (e.g., dynamically enabling, hiding, or setting values), you can use a **Client Script** instead.

Example:

```js
frappe.ui.form.on('Sales Invoice', {
    refresh: function(frm) {
        frm.toggle_display('credit_limit', frm.doc.customer_type === 'Credit');
    }
});
```

This gives you greater flexibility to control field behavior programmatically.

---

## 6. Summary

| Method | When to Use | Example |
|--------|--------------|---------|
| **Depends On (eval)** | Simple condition for visibility | `eval:doc.status === "Active"` |
| **Client Script** | Complex or multi-step logic | `frm.toggle_display('field', condition)` |

---

## 7. Common Pitfalls

- Ensure the `field_name` is spelled exactly as defined in the Doctype.
- String values must be enclosed in quotes `" "`.
- Use `===` for strict equality comparison.
- If using numeric or boolean values, omit quotes (e.g., `eval:doc.is_active === 1`).

---

## References

- [ERPNext Customization Guide](https://docs.erpnext.com/docs/user/manual/en/customize-erpnext/customize-form)
- [Frappe Framework Client Scripts](https://frappeframework.com/docs/user/en/api/form)
