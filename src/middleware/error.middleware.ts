import { Request, Response, NextFunction } from 'express';
import { AppError } from '@/utils/errors';
import { logger } from '@/utils/logger';
import { config } from '@/config/environment';

interface ErrorResponse {
  success: false;
  error: {
    message: string;
    code?: string;
    statusCode: number;
    details?: any;
    stack?: string;
  };
  timestamp: string;
  path: string;
  method: string;
  requestId?: string;
}

export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  // Generate request ID for tracking
  const requestId = (req.headers['x-request-id'] as string) || 
                   `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  // Default error values
  let statusCode = 500;
  let message = 'Internal Server Error';
  let errorCode = 'INTERNAL_ERROR';
  let details: any = undefined;

  // Handle different error types
  if (error instanceof AppError) {
    statusCode = error.statusCode;
    message = error.message;
    errorCode = error.errorCode || 'APP_ERROR';
  } else if (error.name === 'ValidationError') {
    statusCode = 400;
    message = 'Validation failed';
    errorCode = 'VALIDATION_ERROR';
    details = error.message;
  } else if (error.name === 'JsonWebTokenError') {
    statusCode = 401;
    message = 'Invalid token';
    errorCode = 'INVALID_TOKEN';
  } else if (error.name === 'TokenExpiredError') {
    statusCode = 401;
    message = 'Token expired';
    errorCode = 'TOKEN_EXPIRED';
  } else if (error.name === 'CastError') {
    statusCode = 400;
    message = 'Invalid ID format';
    errorCode = 'INVALID_ID';
  } else if (error.name === 'MongoError' || error.name === 'MongoServerError') {
    statusCode = 500;
    message = 'Database error';
    errorCode = 'DATABASE_ERROR';
  }

  // Log error
  const errorLog = {
    requestId,
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
      statusCode,
      errorCode
    },
    request: {
      method: req.method,
      url: req.url,
      headers: req.headers,
      body: req.body,
      params: req.params,
      query: req.query,
      ip: req.ip,
      userAgent: req.get('User-Agent')
    },
    user: (req as any).user ? {
      id: (req as any).user.id,
      email: (req as any).user.email,
      role: (req as any).user.role
    } : null
  };

  // Log based on severity
  if (statusCode >= 500) {
    logger.error('Server error occurred', errorLog);
  } else if (statusCode >= 400) {
    logger.warn('Client error occurred', errorLog);
  } else {
    logger.info('Request completed with error', errorLog);
  }

  // Prepare error response
  const errorResponse: ErrorResponse = {
    success: false,
    error: {
      message,
      code: errorCode,
      statusCode,
      details
    },
    timestamp: new Date().toISOString(),
    path: req.path,
    method: req.method,
    requestId
  };

  // Include stack trace in development
  if (config.nodeEnv === 'development' && error.stack) {
    errorResponse.error.stack = error.stack;
  }

  // Send error response
  res.status(statusCode).json(errorResponse);
};

// Handle 404 errors
export const notFoundHandler = (req: Request, res: Response): void => {
  const errorResponse: ErrorResponse = {
    success: false,
    error: {
      message: `Route ${req.method} ${req.path} not found`,
      code: 'ROUTE_NOT_FOUND',
      statusCode: 404
    },
    timestamp: new Date().toISOString(),
    path: req.path,
    method: req.method
  };

  logger.warn('Route not found', {
    method: req.method,
    path: req.path,
    ip: req.ip,
    userAgent: req.get('User-Agent')
  });

  res.status(404).json(errorResponse);
};

// Handle uncaught exceptions
export const handleUncaughtException = (error: Error): void => {
  logger.error('Uncaught Exception', {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack
    }
  });

  // Graceful shutdown
  process.exit(1);
};

// Handle unhandled promise rejections
export const handleUnhandledRejection = (reason: any, promise: Promise<any>): void => {
  logger.error('Unhandled Promise Rejection', {
    reason: reason instanceof Error ? {
      name: reason.name,
      message: reason.message,
      stack: reason.stack
    } : reason,
    promise: promise.toString()
  });

  // Graceful shutdown
  process.exit(1);
};