export type Trigger = "bid_received" | "any_rank_change" | "l1_rank_change";
export type Auction = {
  id: string;
  reference_id: string;
  name: string;
  bid_close_at: string;
  forced_close_at: string;
  status: string;
  current_lowest_bid: number | null;
};
export type Detail = Auction & {
  bid_start_at: string;
  pickup_at: string;
  trigger_window_minutes: number;
  extension_duration_minutes: number;
  extension_trigger: Trigger;
  bids: Array<{
    id: string;
    supplier_name: string;
    total_amount: number;
    rank: number;
    submitted_at: string;
    transit_time_days: number;
    validity_days: number;
  }>;
  activity_logs: Array<{
    id: string;
    event_type: string;
    message: string;
    metadata_json: Record<string, string>;
    created_at: string;
  }>;
};

const baseUrl = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok)
    throw new Error((await response.json()).detail ?? "Request failed");
  return response.json();
}
export const listAuctions = () => request<Auction[]>("/auctions");
export const getAuction = (id: string) => request<Detail>(`/auctions/${id}`);
export const createAuction = (payload: Record<string, unknown>) =>
  request<Detail>("/auctions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const submitBid = (id: string, payload: Record<string, unknown>) =>
  request(`/auctions/${id}/bids`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
