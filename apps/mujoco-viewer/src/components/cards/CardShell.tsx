import type { ReactNode } from "react";

interface CardShellProps {
  title: string;
  children: ReactNode;
  subtitle?: string;
  className?: string;
  tone?: "default" | "warning" | "error";
}

export function CardShell({ title, subtitle, children, className = "", tone = "default" }: CardShellProps) {
  return (
    <section className={`viewer-card viewer-card--${tone} ${className}`.trim()} data-component="viewer-card">
      <header className="viewer-card__header">
        <h2 className="viewer-card__title">{title}</h2>
        {subtitle !== undefined ? <p className="viewer-card__subtitle">{subtitle}</p> : null}
      </header>
      <div className="viewer-card__body">{children}</div>
    </section>
  );
}

