import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import { config } from '@/config/environment';
import { logger, requestLogger } from '@/utils/logger';
import { errorHandler, notFoundHandler } from '@/middleware/error.middleware';
import { db } from '@/config/database';
import { redis } from '@/config/redis';

// Import routes (will be created)
// import authRoutes from '@/routes/auth.routes';
// import fighterRoutes from '@/routes/fighter.routes';
// import eventRoutes from '@/routes/event.routes';
// import contentRoutes from '@/routes/content.routes';

export class App {
  public app: express.Application;

  constructor() {
    this.app = express();
    this.initializeMiddleware();
    this.initializeRoutes();
    this.initializeErrorHandling();
  }

  private initializeMiddleware(): void {
    // Security middleware
    this.app.use(helmet({
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          styleSrc: ["'self'", "'unsafe-inline'"],
          scriptSrc: ["'self'"],
          imgSrc: ["'self'", "data:", "https:"],
        },
      },
      hsts: {
        maxAge: 31536000,
        includeSubDomains: true,
        preload: true
      }
    }));

    // CORS configuration
    this.app.use(cors({
      origin: config.cors.origin,
      credentials: config.cors.credentials,
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowedHeaders: [
        'Origin',
        'X-Requested-With',
        'Content-Type',
        'Accept',
        'Authorization',
        'X-API-Key',
        'X-Request-ID'
      ],
      exposedHeaders: ['X-Total-Count', 'X-Page-Count']
    }));

    // Compression
    this.app.use(compression());

    // Request parsing
    this.app.use(express.json({ 
      limit: '10mb',
      verify: (req: any, _res, buf) => {
        req.rawBody = buf;
      }
    }));
    this.app.use(express.urlencoded({ extended: true, limit: '10mb' }));

    // Rate limiting
    const limiter = rateLimit({
      windowMs: config.security.rateLimit.windowMs,
      max: config.security.rateLimit.maxRequests,
      message: {
        success: false,
        error: {
          message: 'Too many requests from this IP, please try again later',
          code: 'RATE_LIMIT_EXCEEDED',
          statusCode: 429
        },
        timestamp: new Date().toISOString()
      },
      standardHeaders: true,
      legacyHeaders: false,
      skip: (req) => {
        // Skip rate limiting for health checks
        return req.path === '/health' || req.path === '/api/health';
      }
    });

    this.app.use('/api/', limiter);

    // Request logging
    this.app.use((req, res, next) => {
      const startTime = Date.now();
      
      // Generate request ID
      const requestId = req.headers['x-request-id'] as string || 
                       `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      req.headers['x-request-id'] = requestId;
      res.setHeader('x-request-id', requestId);

      // Log request
      requestLogger.info('Incoming request', {
        requestId,
        method: req.method,
        url: req.url,
        ip: req.ip,
        userAgent: req.get('User-Agent'),
        contentType: req.get('Content-Type'),
        contentLength: req.get('Content-Length')
      });

      // Log response
      res.on('finish', () => {
        const duration = Date.now() - startTime;
        requestLogger.info('Request completed', {
          requestId,
          method: req.method,
          url: req.url,
          statusCode: res.statusCode,
          duration,
          contentLength: res.get('Content-Length')
        });
      });

      next();
    });

    // Trust proxy (for reverse proxy setups)
    this.app.set('trust proxy', 1);
  }

  private initializeRoutes(): void {
    // Health check endpoint
    this.app.get('/health', async (_req, res) => {
      try {
        const dbHealth = await db.healthCheck();
        const redisHealth = await redis.healthCheck();

        const health = {
          status: 'ok',
          timestamp: new Date().toISOString(),
          version: process.env.npm_package_version || '1.0.0',
          environment: config.nodeEnv,
          services: {
            database: dbHealth ? 'healthy' : 'unhealthy',
            redis: redisHealth ? 'healthy' : 'unhealthy'
          },
          uptime: process.uptime(),
          memory: process.memoryUsage(),
          cpu: process.cpuUsage()
        };

        const overallHealth = dbHealth && redisHealth;
        res.status(overallHealth ? 200 : 503).json(health);
      } catch (error) {
        logger.error('Health check failed', error);
        res.status(503).json({
          status: 'error',
          timestamp: new Date().toISOString(),
          message: 'Health check failed'
        });
      }
    });

    // API info endpoint
    this.app.get('/api', (_req, res) => {
      res.json({
        name: 'MMA Database API',
        version: process.env.npm_package_version || '1.0.0',
        description: 'Comprehensive MMA database backend service',
        environment: config.nodeEnv,
        timestamp: new Date().toISOString(),
        endpoints: {
          health: '/health',
          docs: '/api/docs',
          auth: '/api/v1/auth',
          fighters: '/api/v1/fighters',
          events: '/api/v1/events',
          content: '/api/v1/content'
        }
      });
    });

    // API routes
    const apiRouter = express.Router();

    // Authentication routes
    // apiRouter.use('/auth', authRoutes);

    // Data routes
    // apiRouter.use('/fighters', fighterRoutes);
    // apiRouter.use('/events', eventRoutes);
    // apiRouter.use('/content', contentRoutes);

    // Mount API router
    this.app.use(`/api/${config.apiVersion}`, apiRouter);

    // Swagger documentation (will be implemented)
    // this.app.use('/api/docs', swaggerUi.serve, swaggerUi.setup(swaggerSpec));
  }

  private initializeErrorHandling(): void {
    // 404 handler
    this.app.use(notFoundHandler);

    // Global error handler
    this.app.use(errorHandler);
  }

  public async initialize(): Promise<void> {
    try {
      // Initialize database connection
      await db.healthCheck();
      logger.info('Database connection established');

      // Initialize Redis connection
      await redis.connect();
      logger.info('Redis connection established');

      logger.info('Application initialized successfully');
    } catch (error) {
      logger.error('Failed to initialize application', error);
      throw error;
    }
  }

  public async shutdown(): Promise<void> {
    try {
      // Close database connections
      await db.close();
      logger.info('Database connections closed');

      // Close Redis connection
      await redis.disconnect();
      logger.info('Redis connection closed');

      logger.info('Application shutdown completed');
    } catch (error) {
      logger.error('Error during application shutdown', error);
      throw error;
    }
  }
}