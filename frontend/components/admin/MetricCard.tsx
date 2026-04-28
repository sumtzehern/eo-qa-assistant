interface MetricCardProps {
  label: string;
  value: string;
  delta: number;
  deltaPositive: boolean;
  icon?: string;
}

export default function MetricCard({
  label,
  value,
  delta,
  deltaPositive,
  icon,
}: MetricCardProps) {
  const deltaColor = deltaPositive ? "#6EE7B7" : "#F87171";
  const deltaSign = delta >= 0 ? "+" : "";

  return (
    <div
      className="rounded-lg p-4"
      style={{
        backgroundColor: "#1C1C1C",
        border: "1px solid #2A2A2A",
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <span
          className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: "#94A3B8" }}
        >
          {label}
        </span>
        {icon && <span className="text-base">{icon}</span>}
      </div>

      <p className="text-2xl font-bold text-white mb-1">{value}</p>

      <p className="text-xs" style={{ color: deltaColor }}>
        {deltaSign}{delta}% vs last week
      </p>
    </div>
  );
}
