# Token-Based Authentication Testing Guide

## Overview
This guide explains how to test the token-based permission management system that was implemented.

## System Architecture
- **External Token Authentication**: System accepts JWT tokens from external systems
- **Department/Role Permissions**: Users get permissions from both their department (branch) and roles
- **Page-Level Access Control**: Frontend middleware checks page permissions before allowing access
- **Admin Interface**: Management pages for departments, roles, permissions, and login records

## Testing Steps

### 1. Generate Test Token

First, generate a test token using the provided script:

```bash
cd backend
python scripts/generate_token.py
```

This will generate a JWT token with test user data. Copy the token for use in testing.

### 2. Access System with Token

Visit any protected page with the token parameter:
```
http://localhost:3000/admin/departments?token=YOUR_JWT_TOKEN_HERE
```

The system will:
1. Extract and validate the JWT token
2. Create/update login record in database
3. Set authentication cookies
4. Redirect to the requested page (if user has permission)

### 3. Test Different User Scenarios

#### Admin User (Full Access)
```python
# In generate_token.py, use:
payload = {
    "user_id": "admin001",
    "user_name": "系统管理员",
    "branch_no": "ADMIN",
    "branch_name": "系统管理部",
    "role_id_list": ["ADMIN"]
}
```

#### Regular User (Limited Access)
```python
# In generate_token.py, use:
payload = {
    "user_id": "user001", 
    "user_name": "普通用户",
    "branch_no": "SALES",
    "branch_name": "销售部",
    "role_id_list": ["SALES_USER"]
}
```

### 4. Test Permission System

#### Setup Test Data
1. **Create Departments**: Use admin interface at `/admin/departments`
   - Add department with code "SALES" and name "销售部"
   - Add department with code "ADMIN" and name "系统管理部"

2. **Create Roles**: Use admin interface at `/admin/roles`
   - Add role with code "ADMIN" and name "管理员"
   - Add role with code "SALES_USER" and name "销售员"

3. **Assign Permissions**: Use admin interface at `/admin/permissions`
   - Give ADMIN role access to all pages
   - Give SALES_USER role access to limited pages (e.g., only agent, metadata)

#### Test Access Control
1. **Admin Access**: Admin users should access all pages including `/admin/*`
2. **Regular User Access**: Regular users should be blocked from `/admin/*` pages
3. **Unauthorized Access**: Users without proper permissions should see Info page with error message

### 5. Test API Endpoints

#### Authentication Required Endpoints
```bash
# Get current user info (requires valid token)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:50020/api/taosha/v1/login-records/current/info

# List entities (requires authentication)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:50020/api/taosha/v1/entities/

# Admin-only endpoints (requires admin role)
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:50020/api/taosha/v1/entities/ \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"code":"TEST","name":"测试部门","type":"department"}'
```

### 6. Test Frontend Features

#### Navigation Menu
- **Regular Users**: Should see standard navigation (Agent, DeepAgents, 猎诈, 元数据)
- **Admin Users**: Should see additional "系统管理" dropdown with admin pages

#### Page Access
- **Protected Pages**: All pages require authentication
- **Admin Pages**: Only admin users can access `/admin/*` pages
- **Error Handling**: Unauthorized access shows Info page with appropriate message

#### Authentication Flow
1. **Token Login**: Access any page with `?token=JWT_TOKEN` parameter
2. **Cookie Storage**: Token stored in httpOnly cookies for security
3. **Auto Redirect**: After login, user redirected to originally requested page
4. **Session Persistence**: Authentication persists across browser sessions

### 7. Database Verification

Check the database tables to verify data is being stored correctly:

```sql
-- Check login records
SELECT * FROM system_login_records ORDER BY last_login_time DESC;

-- Check entities (departments and roles)
SELECT * FROM system_entities ORDER BY type, code;

-- Check pages
SELECT * FROM system_pages ORDER BY path;

-- Check permissions
SELECT 
    e.code as entity_code,
    e.name as entity_name,
    e.type as entity_type,
    p.path as page_path,
    p.name as page_name
FROM system_permissions sp
JOIN system_entities e ON sp.entity_id = e.id
JOIN system_pages p ON sp.page_id = p.id
ORDER BY e.type, e.code, p.path;
```

## Expected Behavior

### Successful Authentication
- User can access permitted pages
- Navigation shows appropriate menu items
- Login record created/updated in database
- Admin users see admin navigation menu

### Failed Authentication
- Invalid/expired tokens redirect to Info page
- Missing permissions show "权限不足" message
- Unauthorized API calls return 401/403 status codes

### Admin Interface
- Full CRUD operations for departments and roles
- Permission assignment with matrix view
- Login record monitoring and statistics
- Bulk operations for permission management

## Troubleshooting

### Common Issues
1. **Token Expired**: Generate new token with `generate_token.py`
2. **Permission Denied**: Check entity permissions in admin interface
3. **Page Not Found**: Ensure pages are synced from config with `/admin/permissions` sync button
4. **Database Errors**: Check database connection and table creation

### Debug Information
- Check browser console for authentication errors
- Review backend logs for token validation issues
- Use browser dev tools to inspect cookies and API calls
- Verify database records match expected user data

## Security Notes

- JWT tokens contain user information but are signed for integrity
- Tokens should be transmitted over HTTPS in production
- Admin permissions should be carefully managed
- Login records provide audit trail for security monitoring
- Cookies are httpOnly to prevent XSS attacks