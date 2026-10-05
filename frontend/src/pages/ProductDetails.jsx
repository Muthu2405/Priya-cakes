import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../services/api.js";
import Receipt from "../components/Receipt.jsx";
import { Notice, dateLabel } from "../components/ui.jsx";

export default function ProductDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [error, setError] = useState("");
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    api.getProduct(id).then(setProduct).catch((e) => setError(e.message));
  }, [id]);

  async function download() {
    setDownloading(true);
    setError("");
    try {
      await api.downloadPdf(id);
    } catch (e) {
      setError(e.message);
    } finally {
      setDownloading(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Delete ${product.name}? This can't be undone.`)) return;
    try {
      await api.deleteProduct(id);
      navigate("/products");
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>{product ? product.name : "Product"}</h1>
        {product && (
          <div className="actions">
            <button type="button" className="btn primary" onClick={download} disabled={downloading}>
              {downloading ? "Preparing PDF…" : "Download PDF"}
            </button>
            <Link className="btn" to={`/products/${id}/edit`}>Edit</Link>
            <button type="button" className="btn danger" onClick={remove}>Delete</button>
          </div>
        )}
      </div>
      <Notice>{error}</Notice>
      {product && (
        <div className="single">
          <Receipt data={product} title={product.name} />
          <p className="muted small">
            Saved {dateLabel(product.created_at)}. Ingredient costs are fixed at the prices from that day.
          </p>
          <Link to="/products">Back to products</Link>
        </div>
      )}
    </>
  );
}
