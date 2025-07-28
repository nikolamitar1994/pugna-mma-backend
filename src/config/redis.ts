import { createClient, RedisClientType } from 'redis';
import { config } from './environment';
import { logger } from '@/utils/logger';

class RedisConnection {
  private client: RedisClientType;
  private static instance: RedisConnection;
  private isConnected: boolean = false;

  private constructor() {
    const clientConfig: any = {
      url: config.redis.url,
      socket: {
        host: config.redis.host,
        port: config.redis.port,
        reconnectStrategy: (retries: number) => {
          const delay = Math.min(retries * 50, 1000);
          logger.warn(`Redis reconnecting in ${delay}ms (attempt ${retries})`);
          return delay;
        },
      },
    };
    
    if (config.redis.password) {
      clientConfig.password = config.redis.password;
    }
    
    this.client = createClient(clientConfig);

    this.setupEventHandlers();
  }

  public static getInstance(): RedisConnection {
    if (!RedisConnection.instance) {
      RedisConnection.instance = new RedisConnection();
    }
    return RedisConnection.instance;
  }

  private setupEventHandlers(): void {
    this.client.on('connect', () => {
      logger.info('Redis client connecting...');
    });

    this.client.on('ready', () => {
      logger.info('Redis client ready');
      this.isConnected = true;
    });

    this.client.on('error', (err) => {
      logger.error('Redis client error', err);
      this.isConnected = false;
    });

    this.client.on('end', () => {
      logger.info('Redis client disconnected');
      this.isConnected = false;
    });

    this.client.on('reconnecting', () => {
      logger.info('Redis client reconnecting...');
    });
  }

  public async connect(): Promise<void> {
    if (!this.isConnected) {
      await this.client.connect();
    }
  }

  public async disconnect(): Promise<void> {
    if (this.isConnected) {
      await this.client.disconnect();
    }
  }

  public getClient(): RedisClientType {
    return this.client;
  }

  public isReady(): boolean {
    return this.isConnected;
  }

  // Caching utilities
  public async get<T>(key: string): Promise<T | null> {
    try {
      const value = await this.client.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error(`Redis GET error for key ${key}`, error);
      return null;
    }
  }

  public async set(
    key: string, 
    value: unknown, 
    ttlSeconds?: number
  ): Promise<boolean> {
    try {
      const serialized = JSON.stringify(value);
      if (ttlSeconds) {
        await this.client.setEx(key, ttlSeconds, serialized);
      } else {
        await this.client.set(key, serialized);
      }
      return true;
    } catch (error) {
      logger.error(`Redis SET error for key ${key}`, error);
      return false;
    }
  }

  public async del(key: string): Promise<boolean> {
    try {
      await this.client.del(key);
      return true;
    } catch (error) {
      logger.error(`Redis DEL error for key ${key}`, error);
      return false;
    }
  }

  public async exists(key: string): Promise<boolean> {
    try {
      const result = await this.client.exists(key);
      return result === 1;
    } catch (error) {
      logger.error(`Redis EXISTS error for key ${key}`, error);
      return false;
    }
  }

  public async expire(key: string, ttlSeconds: number): Promise<boolean> {
    try {
      await this.client.expire(key, ttlSeconds);
      return true;
    } catch (error) {
      logger.error(`Redis EXPIRE error for key ${key}`, error);
      return false;
    }
  }

  // Hash operations
  public async hget<T>(key: string, field: string): Promise<T | null> {
    try {
      const value = await this.client.hGet(key, field);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error(`Redis HGET error for key ${key}, field ${field}`, error);
      return null;
    }
  }

  public async hset(
    key: string, 
    field: string, 
    value: unknown
  ): Promise<boolean> {
    try {
      const serialized = JSON.stringify(value);
      await this.client.hSet(key, field, serialized);
      return true;
    } catch (error) {
      logger.error(`Redis HSET error for key ${key}, field ${field}`, error);
      return false;
    }
  }

  public async hdel(key: string, field: string): Promise<boolean> {
    try {
      await this.client.hDel(key, field);
      return true;
    } catch (error) {
      logger.error(`Redis HDEL error for key ${key}, field ${field}`, error);
      return false;
    }
  }

  // List operations
  public async lpush(key: string, ...values: string[]): Promise<number> {
    try {
      return await this.client.lPush(key, values);
    } catch (error) {
      logger.error(`Redis LPUSH error for key ${key}`, error);
      return 0;
    }
  }

  public async rpop(key: string): Promise<string | null> {
    try {
      return await this.client.rPop(key);
    } catch (error) {
      logger.error(`Redis RPOP error for key ${key}`, error);
      return null;
    }
  }

  // Health check
  public async healthCheck(): Promise<boolean> {
    try {
      const result = await this.client.ping();
      return result === 'PONG';
    } catch (error) {
      logger.error('Redis health check failed', error);
      return false;
    }
  }

  // Cache key patterns
  public static generateKey(prefix: string, ...parts: string[]): string {
    return `mma:${prefix}:${parts.join(':')}`;
  }
}

export const redis = RedisConnection.getInstance();
export { RedisConnection };