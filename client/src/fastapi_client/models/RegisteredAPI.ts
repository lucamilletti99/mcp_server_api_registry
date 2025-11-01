/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Model for a registered API.
 */
export type RegisteredAPI = {
    api_id: string;
    api_name: string;
    description?: (string | null);
    api_endpoint: string;
    documentation_url?: (string | null);
    http_method?: string;
    auth_type?: string;
    status?: string;
    user_who_requested?: (string | null);
    created_at?: (string | null);
    modified_date?: (string | null);
    last_validated?: (string | null);
};

