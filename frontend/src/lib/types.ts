// Membership types
export type MembershipStatus =
  | "PENDING"
  | "ACTIVE"
  | "SUSPENDED"
  | "EXPIRED"
  | "CANCELLED";

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
}

export interface MembershipTypeSummary {
  id: string;
  code: string;
  name: string;
}

export interface Membership {
  id: string;
  user_id: string;
  user: UserSummary;
  membership_type: MembershipTypeSummary;
  status: MembershipStatus;
  start_date: string;
  end_date: string | null;
  created_at: string;
}

// Payment types
export type PaymentStatus = "PENDING" | "CONFIRMED" | "REJECTED" | "REFUNDED";
export type PaymentMethod = "TRANSFER" | "CASH" | "GATEWAY";
export type FeeType = "MONTHLY" | "ANNUAL" | "INSCRIPTION" | "OTHER";

export interface Payment {
  id: string;
  membership_id: string;
  user_email: string;
  user_full_name: string;
  fee_type: FeeType;
  amount_clp: number;
  payment_method: PaymentMethod;
  payment_date: string;
  period_month: number | null;
  period_year: number | null;
  status: PaymentStatus;
  gateway_transaction_id: string | null;
  transfer_proof_url: string | null;
  notes: string | null;
  confirmed_by: string | null;
  confirmed_at: string | null;
  created_at: string;
}

// Event types
export interface Event {
  id: string;
  title: string;
  description: string | null;
  event_date: string;
  location: string | null;
  address: string | null;
  image_url: string | null;
  is_published: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// User types
export interface User {
  id: string;
  email: string;
  full_name: string;
  rut: string | null;
  phone: string | null;
  birth_date: string | null;
  is_active: boolean;
  created_at: string;
}

// Fee rate types
export interface FeeRate {
  id: string;
  fee_type: FeeType;
  membership_type_id: string;
  amount_utm: number;
  utm_to_clp_rate: number | null;
  amount_clp: number | null;
  effective_from: string;
  effective_until: string | null;
}
