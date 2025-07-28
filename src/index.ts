import { App } from './app';
import { config } from '@/config/environment';
import { logger } from '@/utils/logger';
import { 
  handleUncaughtException, 
  handleUnhandledRejection 
} from '@/middleware/error.middleware';

// Handle uncaught exceptions and unhandled rejections
process.on('uncaughtException', handleUncaughtException);
process.on('unhandledRejection', handleUnhandledRejection);

async function startServer(): Promise<void> {
  try {
    // Create and initialize application
    const app = new App();
    await app.initialize();

    // Start HTTP server
    const server = app.app.listen(config.port, () => {
      logger.info(`Server started successfully`, {
        port: config.port,
        environment: config.nodeEnv,
        apiVersion: config.apiVersion,
        pid: process.pid
      });
    });

    // Graceful shutdown handling
    const gracefulShutdown = async (signal: string): Promise<void> => {
      logger.info(`Received ${signal}, starting graceful shutdown`);

      server.close(async () => {
        logger.info('HTTP server closed');

        try {
          await app.shutdown();
          logger.info('Graceful shutdown completed');
          process.exit(0);
        } catch (error) {
          logger.error('Error during graceful shutdown', error);
          process.exit(1);
        }
      });

      // Force shutdown after 30 seconds
      setTimeout(() => {
        logger.error('Forced shutdown due to timeout');
        process.exit(1);
      }, 30000);
    };

    // Listen for termination signals
    process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
    process.on('SIGINT', () => gracefulShutdown('SIGINT'));

    // Handle server errors
    server.on('error', (error: any) => {
      if (error.code === 'EADDRINUSE') {
        logger.error(`Port ${config.port} is already in use`);
      } else {
        logger.error('Server error', error);
      }
      process.exit(1);
    });

  } catch (error) {
    logger.error('Failed to start server', error);
    process.exit(1);
  }
}

// Start the server
startServer().catch((error) => {
  logger.error('Unhandled error during server startup', error);
  process.exit(1);
});