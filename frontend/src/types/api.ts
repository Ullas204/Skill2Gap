export interface ApiError {
  detail: string;
  code: string;
  extra?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data: T;
  error?: ApiError;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
