function SummaryCard({ title, value, subtitle, type }) {
  return (
    <div className={`summary-card ${type || ""}`}>
      <div className="summary-card-top">
        <span>{title}</span>
      </div>

      <div className="summary-value">{value}</div>

      <div className="summary-subtitle">{subtitle}</div>
    </div>
  );
}

export default SummaryCard;
