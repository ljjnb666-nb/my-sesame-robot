type Props = {
  label: string;
  value: string | number | null | undefined;
  tone?: "normal" | "warning" | "danger" | "muted";
};

export function StatusField({ label, value, tone = "normal" }: Props) {
  return (
    <div className={`status-field tone-${tone}`}>
      <span>{label}</span>
      <strong>{value ?? "未知"}</strong>
    </div>
  );
}
