export type Child = Node | string | number | null | undefined | false;

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  options: {
    className?: string;
    text?: string;
    attrs?: Record<string, string>;
    on?: Partial<Record<keyof HTMLElementEventMap, EventListener>>;
  } = {},
  ...children: Child[]
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (options.className) node.className = options.className;
  if (options.text !== undefined) node.textContent = options.text;
  for (const [name, value] of Object.entries(options.attrs ?? {})) node.setAttribute(name, value);
  for (const [name, handler] of Object.entries(options.on ?? {})) {
    node.addEventListener(name, handler as EventListener);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

export function button(label: string, className: string, handler: () => void): HTMLButtonElement {
  return el("button", {
    className,
    text: label,
    attrs: { type: "button" },
    on: { click: () => handler() }
  });
}

export function field(label: string, input: HTMLInputElement | HTMLTextAreaElement): HTMLLabelElement {
  return el("label", { className: "field" }, el("span", { text: label }), input);
}

export function input(type = "text", placeholder = ""): HTMLInputElement {
  return el("input", { attrs: { type, placeholder } });
}

export function formatDate(value: string | null): string {
  if (!value) return "Nunca";
  return new Intl.DateTimeFormat("es-AR", { dateStyle: "short", timeStyle: "short" }).format(new Date(value));
}

export function showToast(message: string, danger = false): void {
  const toast = document.querySelector<HTMLDivElement>("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.className = `toast show${danger ? " danger" : ""}`;
  window.setTimeout(() => { toast.className = "toast"; }, 3200);
}

export function errorMessage(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  return "Ocurrió un error inesperado";
}
