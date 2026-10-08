import { useState } from "react";
import { Plus, X } from "lucide-react";
import EvidenceCard from "../components/EvidenceCard";

function Evidence({ evidence, onAddEvidence }) {
  const [showForm, setShowForm] = useState(false);

  const [formData, setFormData] = useState({
    source: "",
    claim: "",
    confidence: "",
    type: "Field",
  });

  const handleChange = (event) => {
    setFormData({
      ...formData,
      [event.target.name]: event.target.value,
    });
  };

  const handleSubmit = (event) => {
    event.preventDefault();

    if (!formData.source || !formData.claim) {
      return;
    }

    onAddEvidence({
      ...formData,
      confidence: Number(formData.confidence || 80) / 100,
      timestamp: new Date().toLocaleString(),
      freshness: "Just now",
    });

    setFormData({
      source: "",
      claim: "",
      confidence: "",
      type: "Field",
    });

    setShowForm(false);
  };

  return (
    <div className="page">
      <div className="page-header evidence-page-header">
        <div>
          <span className="eyebrow">EVIDENCE MANAGEMENT</span>

          <h1>Evidence</h1>

          <p>Review, inspect and add evidence used in decision-making.</p>
        </div>

        <button className="primary-button" onClick={() => setShowForm(true)}>
          <Plus size={18} />
          Add Evidence
        </button>
      </div>

      {showForm && (
        <div className="form-overlay">
          <div className="evidence-form">
            <div className="form-header">
              <div>
                <span className="eyebrow">NEW EVIDENCE</span>
                <h2>Add Evidence</h2>
              </div>

              <button
                className="close-button"
                onClick={() => setShowForm(false)}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <label>
                Source
                <input
                  name="source"
                  value={formData.source}
                  onChange={handleChange}
                  placeholder="e.g. Field Sensor"
                />
              </label>

              <label>
                Claim / Content
                <textarea
                  name="claim"
                  value={formData.claim}
                  onChange={handleChange}
                  placeholder="Enter evidence claim..."
                  rows="4"
                />
              </label>

              <label>
                Confidence
                <input
                  name="confidence"
                  type="number"
                  min="0"
                  max="100"
                  value={formData.confidence}
                  onChange={handleChange}
                  placeholder="0 - 100"
                />
              </label>

              <label>
                Type
                <select
                  name="type"
                  value={formData.type}
                  onChange={handleChange}
                >
                  <option>Field</option>
                  <option>Sensor</option>
                  <option>Visual</option>
                  <option>Operational</option>
                  <option>Report</option>
                </select>
              </label>

              <button type="submit" className="primary-button full-width">
                Add Evidence
              </button>
            </form>
          </div>
        </div>
      )}

      <div className="evidence-list large-list">
        {evidence.map((item) => (
          <EvidenceCard key={item.id} evidence={item} />
        ))}
      </div>
    </div>
  );
}

export default Evidence;
