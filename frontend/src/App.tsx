import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createAuction, getAuction, listAuctions, submitBid } from "./api";

const money = (value: number | null) =>
  value === null
    ? "—"
    : `₹${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
const date = (value: string) => new Date(value).toLocaleString();

function App() {
  const [selected, setSelected] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [bidding, setBidding] = useState(false);
  const [message, setMessage] = useState("");
  const auctions = useQuery({
    queryKey: ["auctions"],
    queryFn: listAuctions,
    refetchInterval: 10000,
  });
  const detail = useQuery({
    queryKey: ["auction", selected],
    queryFn: () => getAuction(selected!),
    enabled: !!selected,
    refetchInterval: 5000,
  });
  const refresh = () => {
    void auctions.refetch();
    void detail.refetch();
  };
  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(event.currentTarget));
    const dateFields = [
      "bid_start_at",
      "bid_close_at",
      "forced_close_at",
      "pickup_at",
    ];
    const normalized = Object.fromEntries(
      Object.entries(data).map(([key, value]) => [
        key,
        dateFields.includes(key)
          ? new Date(String(value)).toISOString()
          : value,
      ]),
    );
    try {
      const result = await createAuction({
        ...normalized,
        trigger_window_minutes: Number(data.trigger_window_minutes),
        extension_duration_minutes: Number(data.extension_duration_minutes),
      });
      setCreating(false);
      setSelected(result.id);
      refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to create auction",
      );
    }
  }
  async function bid(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const data = Object.fromEntries(new FormData(event.currentTarget));
    try {
      await submitBid(selected, {
        ...data,
        freight_charges: Number(data.freight_charges),
        origin_charges: Number(data.origin_charges),
        destination_charges: Number(data.destination_charges),
        transit_time_days: Number(data.transit_time_days),
        validity_days: Number(data.validity_days),
      });
      setBidding(false);
      setMessage("Bid accepted and ranking refreshed.");
      refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : "Unable to submit bid",
      );
    }
  }
  return (
    <main className="shell">
      <header>
        <div>
          <span className="eyebrow">GOComet / RFQ CONTROL ROOM</span>
          <h1>British Auctions</h1>
          <p className="muted">Transparent, time-bound supplier competition.</p>
        </div>
        <button className="primary" onClick={() => setCreating(true)}>
          + Create RFQ
        </button>
      </header>
      {message && (
        <div className="notice" onClick={() => setMessage("")}>
          {message}
        </div>
      )}
      {creating && (
        <form className="form-card" onSubmit={create}>
          <div className="form-head">
            <h2>Create British Auction</h2>
            <button
              type="button"
              className="close"
              onClick={() => setCreating(false)}
            >
              ×
            </button>
          </div>
          <div className="form-grid">
            <label>
              RFQ name
              <input name="name" required placeholder="Delhi to Mumbai FTL" />
            </label>
            <label>
              Reference ID
              <input name="reference_id" required placeholder="RFQ-2026-001" />
            </label>
            <label>
              Bid starts
              <input name="bid_start_at" type="datetime-local" required />
            </label>
            <label>
              Bid closes
              <input name="bid_close_at" type="datetime-local" required />
            </label>
            <label>
              Forced close
              <input name="forced_close_at" type="datetime-local" required />
            </label>
            <label>
              Pickup / service date
              <input name="pickup_at" type="datetime-local" required />
            </label>
            <label>
              Trigger window (minutes)
              <input
                name="trigger_window_minutes"
                type="number"
                min="1"
                defaultValue="10"
                required
              />
            </label>
            <label>
              Extension duration (minutes)
              <input
                name="extension_duration_minutes"
                type="number"
                min="1"
                defaultValue="5"
                required
              />
            </label>
            <label>
              Extension trigger
              <select name="extension_trigger" defaultValue="bid_received">
                <option value="bid_received">Any bid received</option>
                <option value="any_rank_change">Any rank change</option>
                <option value="l1_rank_change">L1 rank change</option>
              </select>
            </label>
          </div>
          <button className="primary" type="submit">
            Create auction
          </button>
        </form>
      )}
      {auctions.isError && (
        <div className="error">
          API unavailable. Start the services with{" "}
          <code>docker compose up --build</code>.
        </div>
      )}
      <section className="layout">
        <div className="panel">
          <div className="panel-title">
            <h2>Live auctions</h2>
            <span className="count">{auctions.data?.length ?? 0}</span>
          </div>
          <div className="auction-list">
            {auctions.data?.map((a) => (
              <button
                className={`auction-row ${selected === a.id ? "selected" : ""}`}
                onClick={() => setSelected(a.id)}
                key={a.id}
              >
                <div className="row-top">
                  <strong>{a.name}</strong>
                  <span className={`status ${a.status}`}>
                    {a.status.replace("_", " ")}
                  </span>
                </div>
                <span className="muted">{a.reference_id}</span>
                <div className="row-bottom">
                  <span>
                    Lowest <b>{money(a.current_lowest_bid)}</b>
                  </span>
                  <span>Closes {date(a.bid_close_at)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
        <div className="panel detail">
          {detail.data ? (
            <>
              <div className="detail-head">
                <div>
                  <span className="eyebrow">{detail.data.reference_id}</span>
                  <h2>{detail.data.name}</h2>
                </div>
                <div>
                  <span className={`status ${detail.data.status}`}>
                    {detail.data.status.replace("_", " ")}
                  </span>
                  {detail.data.status === "active" && (
                    <button
                      className="secondary"
                      onClick={() => setBidding(true)}
                    >
                      Submit quote
                    </button>
                  )}
                </div>
              </div>
              <div className="metrics">
                <div>
                  <span>Current L1</span>
                  <b>{money(detail.data.current_lowest_bid)}</b>
                </div>
                <div>
                  <span>Bid close</span>
                  <b>{date(detail.data.bid_close_at)}</b>
                </div>
                <div>
                  <span>Forced close</span>
                  <b>{date(detail.data.forced_close_at)}</b>
                </div>
              </div>
              <h3>Supplier ranking</h3>
              <div className="table">
                <div className="table-head">
                  <span>Rank</span>
                  <span>Supplier</span>
                  <span>Bid</span>
                  <span>Transit</span>
                  <span>Validity</span>
                </div>
                {detail.data.bids.map((b) => (
                  <div className="table-row" key={b.id}>
                    <span className={b.rank === 1 ? "l1" : ""}>L{b.rank}</span>
                    <span>{b.supplier_name}</span>
                    <span>
                      <b>{money(b.total_amount)}</b>
                    </span>
                    <span>{b.transit_time_days} days</span>
                    <span>{b.validity_days} days</span>
                  </div>
                ))}
              </div>
              <div className="columns">
                <div>
                  <h3>Configuration</h3>
                  <p>
                    Trigger window{" "}
                    <b>{detail.data.trigger_window_minutes} min</b>
                  </p>
                  <p>
                    Extension{" "}
                    <b>{detail.data.extension_duration_minutes} min</b>
                  </p>
                  <p>
                    Trigger{" "}
                    <b>{detail.data.extension_trigger.replaceAll("_", " ")}</b>
                  </p>
                </div>
                <div>
                  <h3>Activity log</h3>
                  {detail.data.activity_logs.map((log) => (
                    <div className="activity" key={log.id}>
                      <span className="dot" />
                      <div>
                        <b>{log.message}</b>
                        <small>{date(log.created_at)}</small>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="empty">
              <div className="empty-icon">⌁</div>
              <h2>Select an auction</h2>
              <p className="muted">
                Choose an auction to inspect rankings, configuration, and
                extension history.
              </p>
            </div>
          )}
          {bidding && detail.data && (
            <form className="form-card bid-form" onSubmit={bid}>
              <div className="form-head">
                <h2>Submit supplier quote</h2>
                <button
                  type="button"
                  className="close"
                  onClick={() => setBidding(false)}
                >
                  ×
                </button>
              </div>
              <div className="form-grid">
                <label>
                  Supplier name
                  <input name="supplier_name" required />
                </label>
                <label>
                  Freight charges
                  <input
                    name="freight_charges"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                  />
                </label>
                <label>
                  Origin charges
                  <input
                    name="origin_charges"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                  />
                </label>
                <label>
                  Destination charges
                  <input
                    name="destination_charges"
                    type="number"
                    min="0"
                    step="0.01"
                    required
                  />
                </label>
                <label>
                  Transit time (days)
                  <input
                    name="transit_time_days"
                    type="number"
                    min="0"
                    required
                  />
                </label>
                <label>
                  Quote validity (days)
                  <input name="validity_days" type="number" min="1" required />
                </label>
              </div>
              <button className="primary" type="submit">
                Submit bid
              </button>
            </form>
          )}
        </div>
      </section>
    </main>
  );
}
export default App;
