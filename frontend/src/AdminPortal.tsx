import { useState, useEffect } from 'react';

export default function AdminPortal({ authToken }: { authToken: string }) {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchUsers = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/admin/users', {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        setUsers(await res.json());
      } else {
        setError('Failed to fetch users. You may not have admin privileges.');
      }
    } catch (err) {
      setError('Network error loading users.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [authToken]);

  const updateStatus = async (userId: string, status: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/admin/users/${userId}/status`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify({ status })
      });
      if (res.ok) {
        fetchUsers();
      } else {
        alert('Failed to update status');
      }
    } catch (err) {
      alert('Network error');
    }
  };

  const deleteUser = async (userId: string) => {
    if (!window.confirm("Are you sure you want to permanently delete this user?")) return;
    
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        fetchUsers();
      } else {
        alert('Failed to delete user');
      }
    } catch (err) {
      alert('Network error');
    }
  };

  return (
    <div className="glass-card animate-fade-in container my-4 p-4 p-md-5" style={{ maxWidth: '1320px', width: '100%' }}>
      <h2 className="mb-4 pb-3 border-bottom border-secondary">User Access Management</h2>
      
      {error && <div className="alert alert-danger py-2">{error}</div>}
      
      {loading ? (
        <div className="d-flex justify-content-center p-5">
          <div className="spinner-border text-primary" role="status"><span className="visually-hidden">Loading...</span></div>
        </div>
      ) : (
        <div className="table-responsive">
          <table className="table table-hover align-middle bg-transparent text-body">
            <thead>
              <tr className="border-secondary text-secondary">
                <th className="py-3">Email</th>
                <th className="py-3">Role</th>
                <th className="py-3">Status</th>
                <th className="py-3 text-end">Action</th>
                <th className="py-3 text-center">Remove User</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className="border-secondary">
                  <td className="py-3">{user.email}</td>
                  <td className="py-3 text-capitalize">
                    <span className={`badge ${user.role === 'admin' ? 'bg-primary' : 'bg-secondary'}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className={`badge ${user.approval_status === 'APPROVED' ? 'bg-success' : user.approval_status === 'REJECTED' ? 'bg-danger' : 'bg-warning text-dark'}`}>
                      {user.approval_status}
                    </span>
                  </td>
                  <td className="py-3 text-end">
                    <div className="d-flex gap-2 justify-content-end align-items-center">
                      {user.approval_status !== 'APPROVED' && (
                        <button onClick={() => updateStatus(user.id, 'APPROVED')} className="btn btn-sm btn-outline-success">Accept</button>
                      )}
                      {user.approval_status !== 'PAUSED' && user.approval_status !== 'PENDING' && user.approval_status !== 'REJECTED' && (
                        <button onClick={() => updateStatus(user.id, 'PAUSED')} className="btn btn-sm btn-outline-warning">Pause</button>
                      )}
                    </div>
                  </td>
                  <td className="py-3 text-center align-middle">
                    <div className="d-flex justify-content-center align-items-center" style={{ height: '100%' }}>
                      <button onClick={() => deleteUser(user.id)} className="btn btn-sm btn-danger shadow-sm" title="Delete User">
                        <i className="bi bi-trash-fill"></i>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-5 text-center text-secondary">No other users registered yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
