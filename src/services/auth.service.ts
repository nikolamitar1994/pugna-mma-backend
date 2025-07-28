import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { config } from '@/config/environment';
import { db } from '@/config/database';
import { redis } from '@/config/redis';
import { logger } from '@/utils/logger';
import { 
  CreateUserRequest, 
  LoginRequest, 
  User, 
  TokenPair, 
  JWTPayload 
} from '@/types/auth.types';
import { AppError } from '@/utils/errors';

export class AuthService {
  private readonly JWT_SECRET = config.jwt.secret;
  private readonly JWT_REFRESH_SECRET = config.jwt.refreshSecret;
  private readonly JWT_EXPIRES_IN = config.jwt.expiresIn;
  private readonly JWT_REFRESH_EXPIRES_IN = config.jwt.refreshExpiresIn;
  private readonly BCRYPT_ROUNDS = config.security.bcryptRounds;

  async createUser(userData: CreateUserRequest): Promise<User> {
    try {
      // Check if user already exists
      const existingUser = await this.findUserByEmail(userData.email);
      if (existingUser) {
        throw new AppError('User already exists with this email', 409);
      }

      // Hash password
      const passwordHash = await bcrypt.hash(userData.password, this.BCRYPT_ROUNDS);

      // Create user
      const query = `
        INSERT INTO users (email, password_hash, first_name, last_name, role)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id, email, first_name, last_name, role, is_verified, is_active, created_at
      `;

      const result = await db.query(query, [
        userData.email,
        passwordHash,
        userData.firstName,
        userData.lastName,
        userData.role || 'user'
      ]);

      const user = result.rows[0];
      logger.info('User created successfully', { userId: user.id, email: user.email });

      return this.mapDatabaseUserToUser(user);
    } catch (error) {
      logger.error('Failed to create user', { email: userData.email, error });
      throw error;
    }
  }

  async authenticateUser(loginData: LoginRequest): Promise<{ user: User; tokens: TokenPair }> {
    try {
      // Find user by email
      const user = await this.findUserByEmail(loginData.email);
      if (!user) {
        throw new AppError('Invalid credentials', 401);
      }

      // Check if user is active
      if (!user.isActive) {
        throw new AppError('Account is deactivated', 401);
      }

      // Verify password
      const isPasswordValid = await bcrypt.compare(loginData.password, user.passwordHash);
      if (!isPasswordValid) {
        throw new AppError('Invalid credentials', 401);
      }

      // Generate tokens
      const tokens = await this.generateTokens(user);

      // Update last login
      await this.updateLastLogin(user.id);

      // Remove sensitive data
      const { passwordHash, ...userWithoutPassword } = user;

      logger.info('User authenticated successfully', { userId: user.id, email: user.email });

      return {
        user: userWithoutPassword as User,
        tokens
      };
    } catch (error) {
      logger.error('Authentication failed', { email: loginData.email, error });
      throw error;
    }
  }

  async generateTokens(user: User | any): Promise<TokenPair> {
    try {
      const payload: JWTPayload = {
        userId: user.id,
        email: user.email,
        role: user.role,
        type: 'access'
      };

      const refreshPayload: JWTPayload = {
        userId: user.id,
        email: user.email,
        role: user.role,
        type: 'refresh'
      };

      const accessToken = jwt.sign(payload, this.JWT_SECRET, {
        expiresIn: this.JWT_EXPIRES_IN,
        issuer: 'mma-api',
        audience: 'mma-clients'
      } as jwt.SignOptions);

      const refreshToken = jwt.sign(refreshPayload, this.JWT_REFRESH_SECRET, {
        expiresIn: this.JWT_REFRESH_EXPIRES_IN,
        issuer: 'mma-api',
        audience: 'mma-clients'
      } as jwt.SignOptions);

      // Store refresh token in Redis
      const refreshTokenKey = `refresh_token:${user.id}`;
      await redis.set(refreshTokenKey, refreshToken, 7 * 24 * 60 * 60); // 7 days

      return {
        accessToken,
        refreshToken,
        expiresIn: this.JWT_EXPIRES_IN
      };
    } catch (error) {
      logger.error('Failed to generate tokens', { userId: user.id, error });
      throw new AppError('Failed to generate authentication tokens', 500);
    }
  }

  async refreshTokens(refreshToken: string): Promise<TokenPair> {
    try {
      // Verify refresh token
      const decoded = jwt.verify(refreshToken, this.JWT_REFRESH_SECRET) as JWTPayload;

      if (decoded.type !== 'refresh') {
        throw new AppError('Invalid token type', 401);
      }

      // Check if refresh token exists in Redis
      const refreshTokenKey = `refresh_token:${decoded.userId}`;
      const storedToken = await redis.get<string>(refreshTokenKey);

      if (!storedToken || storedToken !== refreshToken) {
        throw new AppError('Invalid refresh token', 401);
      }

      // Get user data
      const user = await this.findUserById(decoded.userId);
      if (!user || !user.isActive) {
        throw new AppError('User not found or inactive', 401);
      }

      // Generate new tokens
      const tokens = await this.generateTokens(user);

      logger.info('Tokens refreshed successfully', { userId: user.id });

      return tokens;
    } catch (error) {
      if (error instanceof jwt.JsonWebTokenError) {
        throw new AppError('Invalid refresh token', 401);
      }
      throw error;
    }
  }

  async verifyToken(token: string): Promise<JWTPayload> {
    try {
      const decoded = jwt.verify(token, this.JWT_SECRET) as JWTPayload;
      
      if (decoded.type !== 'access') {
        throw new AppError('Invalid token type', 401);
      }

      return decoded;
    } catch (error) {
      if (error instanceof jwt.JsonWebTokenError) {
        throw new AppError('Invalid or expired token', 401);
      }
      throw error;
    }
  }

  async logout(userId: string): Promise<void> {
    try {
      // Remove refresh token from Redis
      const refreshTokenKey = `refresh_token:${userId}`;
      await redis.del(refreshTokenKey);

      logger.info('User logged out successfully', { userId });
    } catch (error) {
      logger.error('Failed to logout user', { userId, error });
      throw new AppError('Failed to logout', 500);
    }
  }

  async changePassword(
    userId: string, 
    currentPassword: string, 
    newPassword: string
  ): Promise<void> {
    try {
      // Get user with password
      const user = await this.findUserById(userId, true);
      if (!user) {
        throw new AppError('User not found', 404);
      }

      // Verify current password
      const isCurrentPasswordValid = await bcrypt.compare(currentPassword, user.passwordHash);
      if (!isCurrentPasswordValid) {
        throw new AppError('Current password is incorrect', 400);
      }

      // Hash new password
      const newPasswordHash = await bcrypt.hash(newPassword, this.BCRYPT_ROUNDS);

      // Update password
      const query = 'UPDATE users SET password_hash = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2';
      await db.query(query, [newPasswordHash, userId]);

      // Invalidate all refresh tokens for this user
      const refreshTokenKey = `refresh_token:${userId}`;
      await redis.del(refreshTokenKey);

      logger.info('Password changed successfully', { userId });
    } catch (error) {
      logger.error('Failed to change password', { userId, error });
      throw error;
    }
  }

  private async findUserByEmail(email: string, includePassword: boolean = true): Promise<any> {
    const fields = includePassword 
      ? 'id, email, password_hash, first_name, last_name, role, is_verified, is_active, last_login, created_at, updated_at'
      : 'id, email, first_name, last_name, role, is_verified, is_active, last_login, created_at, updated_at';

    const query = `SELECT ${fields} FROM users WHERE email = $1`;
    const result = await db.query(query, [email]);

    return result.rows[0] || null;
  }

  private async findUserById(userId: string, includePassword: boolean = false): Promise<any> {
    const fields = includePassword 
      ? 'id, email, password_hash, first_name, last_name, role, is_verified, is_active, last_login, created_at, updated_at'
      : 'id, email, first_name, last_name, role, is_verified, is_active, last_login, created_at, updated_at';

    const query = `SELECT ${fields} FROM users WHERE id = $1`;
    const result = await db.query(query, [userId]);

    return result.rows[0] || null;
  }

  private async updateLastLogin(userId: string): Promise<void> {
    const query = 'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = $1';
    await db.query(query, [userId]);
  }

  private mapDatabaseUserToUser(dbUser: any): User {
    return {
      id: dbUser.id,
      email: dbUser.email,
      firstName: dbUser.first_name,
      lastName: dbUser.last_name,
      role: dbUser.role,
      isVerified: dbUser.is_verified,
      isActive: dbUser.is_active,
      lastLogin: dbUser.last_login,
      createdAt: dbUser.created_at,
      updatedAt: dbUser.updated_at
    };
  }
}