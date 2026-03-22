/**
 * Obsidian Plugin Performance Benchmarking Framework
 *
 * Measures:
 * - Plugin load time
 * - Modal/Settings pane performance
 * - Command execution latency
 * - Memory footprint
 * - Network latency (HTTP/WebSocket)
 */

interface BenchmarkResult {
  testName: string;
  durationMs: number;
  timestamp: string;
  status: 'success' | 'error';
  errorMessage?: string;
  metadata?: Record<string, any>;
}

interface PerformanceMetrics {
  testName: string;
  runs: number;
  minMs: number;
  maxMs: number;
  meanMs: number;
  medianMs: number;
  stddevMs: number;
  p95Ms: number;
  p99Ms: number;
}

/**
 * Performance measurement utilities
 */
export class PerformanceProfiler {
  private baselineMemory: number = 0;
  private baselineTime: number = 0;

  /**
   * Capture baseline measurements
   */
  captureBaseline(): Record<string, any> {
    this.baselineTime = performance.now();
    if (typeof performance.memory !== 'undefined') {
      this.baselineMemory = performance.memory.usedJSHeapSize;
    }

    return {
      timestamp: new Date().toISOString(),
      baselineMemory: this.baselineMemory,
      platform: navigator.platform,
      userAgent: navigator.userAgent,
    };
  }

  /**
   * Measure elapsed time since baseline
   */
  elapsedMs(): number {
    return performance.now() - this.baselineTime;
  }

  /**
   * Measure memory delta
   */
  memoryDeltaMb(): number {
    if (typeof performance.memory !== 'undefined') {
      const currentMemory = performance.memory.usedJSHeapSize;
      return (currentMemory - this.baselineMemory) / 1024 / 1024;
    }
    return 0;
  }

  /**
   * Measure current heap size
   */
  heapSizeMb(): number {
    if (typeof performance.memory !== 'undefined') {
      return performance.memory.usedJSHeapSize / 1024 / 1024;
    }
    return 0;
  }
}

/**
 * Latency measurement utilities
 */
export class LatencyMeasurer {
  /**
   * Measure HTTP request latency
   */
  static async measureHttpLatency(
    url: string,
    method: string = 'GET',
    payload?: Record<string, any>,
    timeout: number = 5000,
  ): Promise<[number, string | null]> {
    const startTime = performance.now();
    let errorMsg: string | null = null;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: payload ? JSON.stringify(payload) : undefined,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        errorMsg = `HTTP ${response.status}`;
      } else {
        await response.json();
      }
    } catch (error) {
      errorMsg = String(error);
    }

    const durationMs = performance.now() - startTime;
    return [durationMs, errorMsg];
  }

  /**
   * Measure DOM operation latency
   */
  static measureDomOperation(
    operation: () => void,
  ): [number, Error | null] {
    const startTime = performance.now();
    let error: Error | null = null;

    try {
      operation();
    } catch (e) {
      error = e instanceof Error ? e : new Error(String(e));
    }

    const durationMs = performance.now() - startTime;
    return [durationMs, error];
  }

  /**
   * Measure event handling latency
   */
  static async measureEventLatency(
    element: HTMLElement,
    eventType: string,
    handler: (event: Event) => Promise<void> | void,
    timeout: number = 5000,
  ): Promise<[number, Error | null]> {
    return new Promise((resolve) => {
      const timeoutId = setTimeout(() => {
        element.removeEventListener(eventType, listener);
        resolve([timeout, new Error('Timeout')]);
      }, timeout);

      const startTime = performance.now();
      let error: Error | null = null;

      const listener = async (event: Event) => {
        try {
          await handler(event);
        } catch (e) {
          error = e instanceof Error ? e : new Error(String(e));
        }
        clearTimeout(timeoutId);
        element.removeEventListener(eventType, listener);
        resolve([performance.now() - startTime, error]);
      };

      element.addEventListener(eventType, listener, { once: true });
      element.dispatchEvent(new Event(eventType));
    });
  }
}

/**
 * Throughput tester
 */
export class ThroughputTester {
  /**
   * Execute concurrent HTTP requests
   */
  static async concurrentRequests(
    url: string,
    payload: Record<string, any>,
    concurrentCount: number,
    timeout: number = 5000,
  ): Promise<Record<string, any>> {
    const durations: number[] = [];
    let errors = 0;
    let successful = 0;

    const makeRequest = async () => {
      const [duration, error] = await LatencyMeasurer.measureHttpLatency(
        url,
        'POST',
        payload,
        timeout,
      );

      if (error) {
        errors++;
      } else {
        successful++;
        durations.push(duration);
      }
    };

    // Execute concurrent requests
    await Promise.all(
      Array.from({ length: concurrentCount }).map(() => makeRequest()),
    );

    if (durations.length === 0) {
      return {
        concurrentCount,
        successful: 0,
        errors: concurrentCount,
        errorRate: 1.0,
        latency: {},
      };
    }

    durations.sort((a, b) => a - b);
    const p95Idx = Math.floor(durations.length * 0.95);
    const p99Idx = Math.floor(durations.length * 0.99);

    return {
      concurrentCount,
      successful,
      errors,
      errorRate: errors / concurrentCount,
      latency: {
        minMs: Math.min(...durations),
        maxMs: Math.max(...durations),
        meanMs: durations.reduce((a, b) => a + b, 0) / durations.length,
        medianMs: durations[Math.floor(durations.length / 2)],
        p95Ms: durations[p95Idx],
        p99Ms: durations[p99Idx],
      },
    };
  }
}

/**
 * Plugin benchmark suite
 */
export class PluginBenchmarkSuite {
  private profiler = new PerformanceProfiler();
  private results: BenchmarkResult[] = [];

  /**
   * Initialize benchmarks
   */
  async initialize(): Promise<void> {
    this.profiler.captureBaseline();
  }

  /**
   * Benchmark plugin load time
   */
  async benchmarkPluginLoad(): Promise<PerformanceMetrics> {
    const runs = 5;
    const durations: number[] = [];

    for (let i = 0; i < runs; i++) {
      const startTime = performance.now();

      // Simulate plugin initialization
      await new Promise((resolve) => setTimeout(resolve, 10));

      const duration = performance.now() - startTime;
      durations.push(duration);
    }

    return this.calculateMetrics('plugin_load', durations);
  }

  /**
   * Benchmark modal open time
   */
  async benchmarkModalPerformance(modalElement: HTMLElement): Promise<PerformanceMetrics> {
    const runs = 10;
    const durations: number[] = [];

    for (let i = 0; i < runs; i++) {
      const [duration, error] = LatencyMeasurer.measureDomOperation(() => {
        modalElement.style.display = 'block';
        // Trigger reflow
        void modalElement.offsetHeight;
        modalElement.style.display = 'none';
      });

      if (!error) {
        durations.push(duration);
      }
    }

    return this.calculateMetrics('modal_open', durations);
  }

  /**
   * Benchmark settings pane load
   */
  async benchmarkSettingsPaneLoad(settingsElement: HTMLElement): Promise<PerformanceMetrics> {
    const runs = 5;
    const durations: number[] = [];

    for (let i = 0; i < runs; i++) {
      const [duration, error] = LatencyMeasurer.measureDomOperation(() => {
        // Simulate settings pane initialization
        settingsElement.innerHTML = '<div>Settings content</div>';
        void settingsElement.offsetHeight;
      });

      if (!error) {
        durations.push(duration);
      }
    }

    return this.calculateMetrics('settings_pane_load', durations);
  }

  /**
   * Benchmark HTTP request latency
   */
  async benchmarkHttpLatency(url: string): Promise<PerformanceMetrics> {
    const runs = 10;
    const durations: number[] = [];

    for (let i = 0; i < runs; i++) {
      const [duration, error] = await LatencyMeasurer.measureHttpLatency(url);

      if (!error) {
        durations.push(duration);
      }
    }

    return this.calculateMetrics('http_latency', durations);
  }

  /**
   * Benchmark concurrent HTTP requests
   */
  async benchmarkConcurrentHttp(url: string): Promise<Record<string, any>> {
    const payload = { test: true };
    const results: Record<string, any> = {};

    for (const concurrency of [10, 50, 100]) {
      results[`concurrent_${concurrency}`] = await ThroughputTester.concurrentRequests(
        url,
        payload,
        concurrency,
      );
    }

    return results;
  }

  /**
   * Benchmark memory usage
   */
  benchmarkMemory(): Record<string, any> {
    return {
      heapUsageMb: this.profiler.heapSizeMb(),
      heapDeltaMb: this.profiler.memoryDeltaMb(),
    };
  }

  /**
   * Calculate aggregated metrics
   */
  private calculateMetrics(testName: string, durations: number[]): PerformanceMetrics {
    if (durations.length === 0) {
      throw new Error(`No successful measurements for ${testName}`);
    }

    const sorted = [...durations].sort((a, b) => a - b);
    const mean = durations.reduce((a, b) => a + b, 0) / durations.length;
    const variance =
      durations.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / durations.length;
    const stddev = Math.sqrt(variance);

    const p95Idx = Math.floor(sorted.length * 0.95);
    const p99Idx = Math.floor(sorted.length * 0.99);

    return {
      testName,
      runs: durations.length,
      minMs: sorted[0],
      maxMs: sorted[sorted.length - 1],
      meanMs: mean,
      medianMs: sorted[Math.floor(sorted.length / 2)],
      stddevMs: stddev,
      p95Ms: sorted[p95Idx],
      p99Ms: sorted[p99Idx],
    };
  }

  /**
   * Run all benchmarks
   */
  async runAll(config: {
    serverUrl?: string;
    modalElement?: HTMLElement;
    settingsElement?: HTMLElement;
  } = {}): Promise<Record<string, any>> {
    const results: Record<string, any> = {
      timestamp: new Date().toISOString(),
      benchmarks: {},
    };

    try {
      // Plugin benchmarks
      results.benchmarks.pluginLoad = await this.benchmarkPluginLoad();

      if (config.modalElement) {
        results.benchmarks.modal = await this.benchmarkModalPerformance(config.modalElement);
      }

      if (config.settingsElement) {
        results.benchmarks.settingsPane = await this.benchmarkSettingsPaneLoad(
          config.settingsElement,
        );
      }

      // Network benchmarks
      const serverUrl = config.serverUrl || 'http://localhost:8000';
      results.benchmarks.httpLatency = await this.benchmarkHttpLatency(serverUrl);
      results.benchmarks.concurrent = await this.benchmarkConcurrentHttp(serverUrl);

      // Memory benchmarks
      results.benchmarks.memory = this.benchmarkMemory();
    } catch (error) {
      results.error = String(error);
    }

    return results;
  }
}

export default PluginBenchmarkSuite;
