import { CardShell } from "./CardShell.js";
import type { ViewerWarning } from "../../viewModels/viewerViewModel.js";

interface WarningCardProps {
  warnings: readonly ViewerWarning[];
}

export function WarningCard({ warnings }: WarningCardProps) {
  const tone = warnings.some((warning) => warning.severity === "error")
    ? "error"
    : warnings.some((warning) => warning.severity === "warning")
      ? "warning"
      : "default";

  return (
    <CardShell
      title="Warnings"
      subtitle={warnings.length === 0 ? "No active warnings" : "Operational notes and omissions"}
      tone={tone}
    >
      {warnings.length === 0 ? (
        <p className="viewer-card__empty">No warnings.</p>
      ) : (
        <ul className="viewer-card__list">
          {warnings.map((warning) => (
            <li key={warning.code} data-severity={warning.severity}>
              <span className="viewer-card__severity">{warning.severity}</span>
              <span className="viewer-card__message">{warning.message}</span>
            </li>
          ))}
        </ul>
      )}
    </CardShell>
  );
}

