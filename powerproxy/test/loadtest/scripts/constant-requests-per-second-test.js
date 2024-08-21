import http from 'k6/http';
import { check } from 'k6';
import { htmlReport } from "https://raw.githubusercontent.com/benc-uk/k6-reporter/main/dist/bundle.js";

export let options = {
  summaryTrendStats: ['avg', 'min', 'max', 'p(70)', 'p(90)', 'p(95)', 'count'],
  scenarios: {
    constant_request_per_second: {
      executor: 'constant-arrival-rate',
      rate:2,
      timeUnit: '1s',
      duration: '2m',
      preAllocatedVUs: 2,
      maxVUs: 60,
      exec: 'constant_executor',
    },
  },
  thresholds: {
    'http_req_duration{scenario:constant_request_per_second}': ['p(90)<1500'], // 90% of requests must complete below 1.5s
  },
};

export function setup() {
  console.log("Adding initial delay of 2 seconds");
}

export function constant_executor() {
  const BASE_URL = "http://0.0.0.0:8000/chat_completions";

  const payload = JSON.stringify({
    "prompt": "Tell me a joke in German",
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const res = http.post(`${BASE_URL}`, payload, params);

  if (res.status === 500 || res.status === 504) {
    console.log(`Response: ${res.body}\nResponse status code: ${res.status}`);
  } else if (res.status === 200) {
    console.log(`Response: ${res.body}\nResponse status code: ${res.status}`);
  }

  check(res, {
    'is status 200': (r) => r.status === 200,
    'is response less than 18000ms': (r) => r.timings.duration <= 180000
  });
}

export function handleSummary(data) {
  return {
    "load-test-summary.html": htmlReport(data),
  };
}
