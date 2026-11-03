/** Thrown by the static provider when the demo cannot answer without the live engine. */
export class ReadOnlyError extends Error {
  constructor(what: string) {
    super(`Demo 模式為唯讀：${what}需要本機引擎（實戰模式）。這裡只能檢視預先用 synthetic 參數算好的結果。`);
    this.name = "ReadOnlyError";
  }
}
