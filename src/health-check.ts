#!/usr/bin/env node

/**
 * Health check script for Docker health checks
 * This script will be used by Docker to verify the application is healthy
 */

import http from 'http';
import { config } from '@/config/environment';

const healthCheck = (): Promise<void> => {
  return new Promise((resolve, reject) => {
    const options = {
      host: 'localhost',
      port: config.port,
      path: '/health',
      timeout: 2000,
    };

    const request = http.request(options, (response) => {
      console.log(`Health check status: ${response.statusCode}`);
      
      if (response.statusCode === 200) {
        resolve();
      } else {
        reject(new Error(`Health check failed with status ${response.statusCode}`));
      }
    });

    request.on('error', (error) => {
      reject(error);
    });

    request.on('timeout', () => {
      request.destroy();
      reject(new Error('Health check timeout'));
    });

    request.end();
  });
};

// Run health check
healthCheck()
  .then(() => {
    console.log('Health check passed');
    process.exit(0);
  })
  .catch((error) => {
    console.error('Health check failed:', error.message);
    process.exit(1);
  });