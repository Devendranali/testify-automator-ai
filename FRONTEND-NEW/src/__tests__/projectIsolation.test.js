import useAppStore from "../state/useAppStore";

test("partitions project state by active project id", () => {
  const initial = useAppStore.getState();
  try {
    useAppStore.getState().setActiveProject({ id: 1, name: "Alpha" });
    useAppStore.getState().setTestCases([{ id: "tc-a" }]);
    useAppStore
      .getState()
      .setUploadedImages([{ id: "img-a", name: "a.png", type: "image/png", size: 1 }]);

    useAppStore.getState().setActiveProject({ id: 2, name: "Beta" });
    expect(useAppStore.getState().testCases.items).toEqual([]);
    expect(useAppStore.getState().uploads.images).toEqual([]);

    useAppStore.getState().setTestCases([{ id: "tc-b" }]);

    useAppStore.getState().setActiveProject({ id: 1, name: "Alpha" });
    expect(useAppStore.getState().testCases.items).toEqual([{ id: "tc-a" }]);
    expect(useAppStore.getState().uploads.images[0]?.name).toBe("a.png");
  } finally {
    useAppStore.setState(initial, true);
    localStorage.clear();
  }
});
