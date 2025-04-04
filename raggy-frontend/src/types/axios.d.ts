declare module 'axios' {
  import { AxiosRequestConfig, AxiosResponse } from 'axios';
  
  export interface InternalAxiosRequestConfig extends AxiosRequestConfig {
    headers: {
      [key: string]: string;
    };
  }
  
  export interface AxiosInstance {
    create(config?: AxiosRequestConfig): AxiosInstance;
    interceptors: {
      request: {
        use(
          onFulfilled?: (config: InternalAxiosRequestConfig) => Promise<InternalAxiosRequestConfig> | InternalAxiosRequestConfig,
          onRejected?: (error: any) => any
        ): number;
      };
      response: {
        use(
          onFulfilled?: (response: AxiosResponse) => AxiosResponse | Promise<AxiosResponse>,
          onRejected?: (error: any) => any
        ): number;
      };
    };
    get<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
    delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>>;
  }
  
  const axios: AxiosInstance;
  export default axios;
} 