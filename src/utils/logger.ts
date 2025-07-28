import winston from 'winston';
import { config } from '@/config/environment';

// Custom log format for development
const developmentFormat = winston.format.combine(
  winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
  winston.format.errors({ stack: true }),
  winston.format.colorize(),
  winston.format.printf(({ level, message, timestamp, ...meta }) => {
    let msg = `${timestamp} [${level}]: ${message}`;
    if (Object.keys(meta).length > 0) {
      msg += `\n${JSON.stringify(meta, null, 2)}`;
    }
    return msg;
  })
);

// JSON format for production
const productionFormat = winston.format.combine(
  winston.format.timestamp(),
  winston.format.errors({ stack: true }),
  winston.format.json()
);

// Create logger instance
export const logger = winston.createLogger({
  level: config.logging.level,
  format: config.nodeEnv === 'production' ? productionFormat : developmentFormat,
  defaultMeta: { 
    service: 'mma-api',
    version: process.env.npm_package_version || '1.0.0',
    environment: config.nodeEnv
  },
  transports: [
    // Console transport
    new winston.transports.Console({
      stderrLevels: ['error'],
    }),
  ],
});

// Add file transports for production
if (config.nodeEnv === 'production') {
  logger.add(
    new winston.transports.File({
      filename: 'logs/error.log',
      level: 'error',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  );

  logger.add(
    new winston.transports.File({
      filename: 'logs/combined.log',
      maxsize: 5242880, // 5MB
      maxFiles: 5,
    })
  );
}

// Request logger middleware
export const requestLogger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { type: 'request' },
  transports: [
    new winston.transports.Console(),
  ],
});

// Performance logger
export const performanceLogger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { type: 'performance' },
  transports: [
    new winston.transports.Console(),
  ],
});

// Database logger
export const dbLogger = winston.createLogger({
  level: 'debug',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  defaultMeta: { type: 'database' },
  transports: [
    new winston.transports.Console({
      level: config.nodeEnv === 'production' ? 'error' : 'debug',
    }),
  ],
});

// Export a function to create child loggers with additional context
export const createChildLogger = (context: Record<string, any>) => {
  return logger.child(context);
};