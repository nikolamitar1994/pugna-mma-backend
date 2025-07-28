import dotenv from 'dotenv';
import Joi from 'joi';

// Load environment variables
dotenv.config();

// Environment validation schema
const envSchema = Joi.object({
  NODE_ENV: Joi.string()
    .valid('development', 'production', 'test')
    .default('development'),
  PORT: Joi.number().default(3000),
  API_VERSION: Joi.string().default('v1'),

  // Database
  DATABASE_URL: Joi.string().uri().required(),
  DATABASE_HOST: Joi.string().default('localhost'),
  DATABASE_PORT: Joi.number().default(5432),
  DATABASE_NAME: Joi.string().required(),
  DATABASE_USER: Joi.string().required(),
  DATABASE_PASSWORD: Joi.string().required(),

  // Redis
  REDIS_URL: Joi.string().uri().required(),
  REDIS_HOST: Joi.string().default('localhost'),
  REDIS_PORT: Joi.number().default(6379),
  REDIS_PASSWORD: Joi.string().allow('').optional(),

  // JWT
  JWT_SECRET: Joi.string().min(32).required(),
  JWT_EXPIRES_IN: Joi.string().default('15m'),
  JWT_REFRESH_SECRET: Joi.string().min(32).required(),
  JWT_REFRESH_EXPIRES_IN: Joi.string().default('7d'),

  // OAuth
  GOOGLE_CLIENT_ID: Joi.string().optional(),
  GOOGLE_CLIENT_SECRET: Joi.string().optional(),
  FACEBOOK_APP_ID: Joi.string().optional(),
  FACEBOOK_APP_SECRET: Joi.string().optional(),

  // External APIs
  OPENAI_API_KEY: Joi.string().optional(),
  WIKIPEDIA_API_URL: Joi.string().uri().default('https://en.wikipedia.org/w/api.php'),

  // Security
  BCRYPT_ROUNDS: Joi.number().min(10).max(15).default(12),
  RATE_LIMIT_WINDOW_MS: Joi.number().default(900000), // 15 minutes
  RATE_LIMIT_MAX_REQUESTS: Joi.number().default(100),

  // CORS
  CORS_ORIGIN: Joi.string().default('http://localhost:3000'),
  CORS_CREDENTIALS: Joi.boolean().default(true),

  // Logging
  LOG_LEVEL: Joi.string()
    .valid('error', 'warn', 'info', 'debug')
    .default('info'),
  LOG_FORMAT: Joi.string()
    .valid('json', 'simple')
    .default('json'),

  // File Upload
  MAX_FILE_SIZE: Joi.number().default(10485760), // 10MB
  UPLOAD_DIR: Joi.string().default('uploads'),

  // Health Check
  HEALTH_CHECK_INTERVAL: Joi.number().default(30000), // 30 seconds
}).unknown(true);

const { error, value: envVars } = envSchema.validate(process.env);

if (error) {
  throw new Error(`Config validation error: ${error.message}`);
}

export const config = {
  nodeEnv: envVars.NODE_ENV as 'development' | 'production' | 'test',
  port: envVars.PORT as number,
  apiVersion: envVars.API_VERSION as string,

  database: {
    url: envVars.DATABASE_URL as string,
    host: envVars.DATABASE_HOST as string,
    port: envVars.DATABASE_PORT as number,
    name: envVars.DATABASE_NAME as string,
    user: envVars.DATABASE_USER as string,
    password: envVars.DATABASE_PASSWORD as string,
  },

  redis: {
    url: envVars.REDIS_URL as string,
    host: envVars.REDIS_HOST as string,
    port: envVars.REDIS_PORT as number,
    password: envVars.REDIS_PASSWORD as string,
  },

  jwt: {
    secret: envVars.JWT_SECRET as string,
    expiresIn: envVars.JWT_EXPIRES_IN as string,
    refreshSecret: envVars.JWT_REFRESH_SECRET as string,
    refreshExpiresIn: envVars.JWT_REFRESH_EXPIRES_IN as string,
  },

  oauth: {
    google: {
      clientId: envVars.GOOGLE_CLIENT_ID as string,
      clientSecret: envVars.GOOGLE_CLIENT_SECRET as string,
    },
    facebook: {
      appId: envVars.FACEBOOK_APP_ID as string,
      appSecret: envVars.FACEBOOK_APP_SECRET as string,
    },
  },

  externalApis: {
    openai: {
      apiKey: envVars.OPENAI_API_KEY as string,
    },
    wikipedia: {
      apiUrl: envVars.WIKIPEDIA_API_URL as string,
    },
  },

  security: {
    bcryptRounds: envVars.BCRYPT_ROUNDS as number,
    rateLimit: {
      windowMs: envVars.RATE_LIMIT_WINDOW_MS as number,
      maxRequests: envVars.RATE_LIMIT_MAX_REQUESTS as number,
    },
  },

  cors: {
    origin: envVars.CORS_ORIGIN?.split(',') || ['http://localhost:3000'],
    credentials: envVars.CORS_CREDENTIALS as boolean,
  },

  logging: {
    level: envVars.LOG_LEVEL as string,
    format: envVars.LOG_FORMAT as 'json' | 'simple',
  },

  upload: {
    maxFileSize: envVars.MAX_FILE_SIZE as number,
    uploadDir: envVars.UPLOAD_DIR as string,
  },

  healthCheck: {
    interval: envVars.HEALTH_CHECK_INTERVAL as number,
  },
} as const;