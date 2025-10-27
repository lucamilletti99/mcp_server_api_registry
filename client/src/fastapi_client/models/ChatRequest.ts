/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatMessage } from './ChatMessage';
/**
 * Request to send a chat message.
 */
export type ChatRequest = {
    messages: Array<ChatMessage>;
    model?: string;
    max_tokens?: number;
};

