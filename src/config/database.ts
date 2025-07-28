import { Pool, PoolConfig } from 'pg';
import { config } from './environment';
import { logger } from '@/utils/logger';

class DatabaseConnection {
  private pool: Pool;
  private static instance: DatabaseConnection;

  private constructor() {
    const poolConfig: PoolConfig = {
      connectionString: config.database.url,
      host: config.database.host,
      port: config.database.port,
      database: config.database.name,
      user: config.database.user,
      password: config.database.password,
      max: 20, // Maximum number of clients in the pool
      idleTimeoutMillis: 30000, // How long a client is allowed to remain idle
      connectionTimeoutMillis: 2000, // How long to wait for a connection
      ssl: config.nodeEnv === 'production' ? { rejectUnauthorized: false } : false,
    };

    this.pool = new Pool(poolConfig);

    // Handle pool events
    this.pool.on('connect', (_client) => {
      logger.info('New database client connected');
    });

    this.pool.on('error', (err) => {
      logger.error('Unexpected error on idle client', err);
    });

    this.pool.on('remove', () => {
      logger.info('Database client removed from pool');
    });
  }

  public static getInstance(): DatabaseConnection {
    if (!DatabaseConnection.instance) {
      DatabaseConnection.instance = new DatabaseConnection();
    }
    return DatabaseConnection.instance;
  }

  public getPool(): Pool {
    return this.pool;
  }

  public async query(text: string, params?: unknown[]): Promise<any> {
    const start = Date.now();
    try {
      const res = await this.pool.query(text, params);
      const duration = Date.now() - start;
      logger.debug('Executed query', { 
        query: text, 
        duration, 
        rows: res.rowCount 
      });
      return res;
    } catch (error) {
      logger.error('Database query error', { 
        query: text, 
        params, 
        error: error instanceof Error ? error.message : 'Unknown error' 
      });
      throw error;
    }
  }

  public async getClient(): Promise<any> {
    return await this.pool.connect();
  }

  public async close(): Promise<void> {
    await this.pool.end();
    logger.info('Database pool closed');
  }

  // Health check method
  public async healthCheck(): Promise<boolean> {
    try {
      const result = await this.query('SELECT NOW()');
      return result.rows.length > 0;
    } catch (error) {
      logger.error('Database health check failed', error);
      return false;
    }
  }

  // Transaction wrapper
  public async transaction<T>(
    callback: (client: any) => Promise<T>
  ): Promise<T> {
    const client = await this.getClient();
    try {
      await client.query('BEGIN');
      const result = await callback(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}

export const db = DatabaseConnection.getInstance();
export { DatabaseConnection };