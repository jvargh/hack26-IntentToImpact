/* Generated from studio.schema.json. Do not edit. */
import type { StudioJob, BuildResult, AnalysisRequest, BuildRequest, RunHistory, SavedRun } from "./contracts";
export declare function jobShape(value: unknown): value is StudioJob;
export declare function buildShape(value: unknown): value is BuildResult;
export declare function inputShape(value: unknown): value is AnalysisRequest;
export declare function requestBuildShape(value: unknown): value is BuildRequest;
export declare function historyShape(value: unknown): value is RunHistory;
export declare function savedRunShape(value: unknown): value is SavedRun;
