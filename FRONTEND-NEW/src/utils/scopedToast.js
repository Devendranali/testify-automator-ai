import { toast as baseToast } from "react-toastify";

let _currentScope = "";

export const setToastScope = (scope) => {
  _currentScope = String(scope || "");
};

const shouldShow = (scope) => {
  const normalized = String(scope || "");
  if (!normalized) return true;
  return normalized === _currentScope;
};

export const createScopedToast = (scope) => ({
  success: (content, options) =>
    shouldShow(scope) ? baseToast.success(content, options) : undefined,
  error: (content, options) =>
    shouldShow(scope) ? baseToast.error(content, options) : undefined,
  info: (content, options) =>
    shouldShow(scope) ? baseToast.info(content, options) : undefined,
  warn: (content, options) =>
    shouldShow(scope) ? baseToast.warn(content, options) : undefined,
  warning: (content, options) =>
    shouldShow(scope) ? baseToast.warning(content, options) : undefined,
  dismiss: baseToast.dismiss,
});

