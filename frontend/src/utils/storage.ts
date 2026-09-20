const REFRESH_TOKEN_KEY = "hire_refresh_token";

export const storage = {
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  },
  setRefreshToken(token: string): void {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  },
  removeRefreshToken(): void {
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};
