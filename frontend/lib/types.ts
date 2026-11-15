export type Status = "ok" | "missing" | "stale";

export interface SourceMeta {
  source?: string;
  source_code?: string;
  url?: string;
  locator?: string | null;
  document_type?: string;
  published_at?: string | null;
  retrieved_at?: string;
  revision?: number;
  derivation?: string | null;
}

export interface Delta {
  value: number;
  unit: "%" | "p.p.";
}

export interface IndicatorItem extends SourceMeta {
  code: string;
  name: string;
  unit: string;
  scope: string;
  frequency: string;
  definition: string;
  period: string;
  status: Status;
  value?: number;
  as_of?: string;
  qoq?: Delta | null;
  yoy?: Delta | null;
  ipca_12m?: { value: number; unit: string; derivation: string };
}

export interface PeriodItem {
  code: string;
  end: string;
  label: string;
}

export interface SeriesPoint extends SourceMeta {
  period_start?: string | null;
  period_end: string;
  value: number;
}

export interface Segment extends SourceMeta {
  code: string;
  label: string;
  status: Status;
  value?: number;
  share_pct?: number;
}

export interface CreditSegments {
  status: Status;
  period: string;
  unit?: string;
  total?: number;
  total_source?: SourceMeta;
  segments?: Segment[];
}

export interface QualityIndicator {
  code: string;
  name: string;
  source: string;
  frequency: string;
  observations: number;
  first_period: string | null;
  last_period: string | null;
  last_retrieved_at: string | null;
  status: Status;
}

export interface EtlRunItem {
  id: number;
  job: string;
  status: string;
  started_at: string;
  ended_at: string | null;
  rows_inserted: number;
  rows_updated: number;
  error: string | null;
}

export interface DataQuality {
  indicators: QualityIndicator[];
  summary: Record<Status, number>;
  runs: EtlRunItem[];
  checked_at: string;
}

export interface Envelope<T> {
  data: T;
  meta: Record<string, unknown> & { generated_at: string; disclaimer: string };
}
