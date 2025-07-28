import { Response, NextFunction } from 'express';
import { AuthService } from '@/services/auth.service';
import { AuthenticationError, AuthorizationError } from '@/utils/errors';
import { logger } from '@/utils/logger';
import { AuthenticatedRequest } from '@/types/auth.types';

const authService = new AuthService();

export interface AuthMiddlewareOptions {
  required?: boolean;
  roles?: string[];
}

export const authenticate = (options: AuthMiddlewareOptions = { required: true }) => {
  return async (req: AuthenticatedRequest, _res: Response, next: NextFunction): Promise<void> => {
    try {
      const authHeader = req.headers.authorization;
      
      if (!authHeader) {
        if (options.required) {
          throw new AuthenticationError('Authorization header is required');
        }
        return next();
      }

      if (!authHeader.startsWith('Bearer ')) {
        throw new AuthenticationError('Invalid authorization header format');
      }

      const token = authHeader.substring(7); // Remove 'Bearer ' prefix

      if (!token) {
        if (options.required) {
          throw new AuthenticationError('Token is required');
        }
        return next();
      }

      // Verify token
      const payload = await authService.verifyToken(token);
      
      // Attach user info to request
      req.userId = payload.userId;
      req.user = {
        id: payload.userId,
        email: payload.email,
        role: payload.role as 'admin' | 'editor' | 'user',
      } as any;

      // Check role authorization if specified
      if (options.roles && options.roles.length > 0) {
        if (!options.roles.includes(payload.role)) {
          throw new AuthorizationError('Insufficient permissions');
        }
      }

      logger.debug('User authenticated successfully', {
        userId: payload.userId,
        role: payload.role,
        endpoint: req.path
      });

      next();
    } catch (error) {
      logger.warn('Authentication failed', {
        error: error instanceof Error ? error.message : 'Unknown error',
        endpoint: req.path,
        userAgent: req.get('User-Agent')
      });
      next(error);
    }
  };
};

// Middleware for optional authentication
export const optionalAuth = authenticate({ required: false });

// Middleware for admin-only access
export const requireAdmin = authenticate({ 
  required: true, 
  roles: ['admin'] 
});

// Middleware for admin or editor access
export const requireEditor = authenticate({ 
  required: true, 
  roles: ['admin', 'editor'] 
});

// Middleware for any authenticated user
export const requireAuth = authenticate({ required: true });