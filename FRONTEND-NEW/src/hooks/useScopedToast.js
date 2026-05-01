import { useMemo } from "react";
import { useLocation } from "react-router-dom";

import { createScopedToast } from "../utils/scopedToast";

export default function useScopedToast() {
  const location = useLocation();
  const scope = location.pathname;
  return useMemo(() => createScopedToast(scope), [scope]);
}
