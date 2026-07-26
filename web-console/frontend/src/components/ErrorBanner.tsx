type Props = {
  message: string | null;
  tone?: "success" | "info" | "warning" | "danger";
};

export function ErrorBanner({ message, tone = "danger" }: Props) {
  if (!message) return null;
  return (
    <div className={`error-banner tone-${tone}`} role="status">
      {message}
    </div>
  );
}
