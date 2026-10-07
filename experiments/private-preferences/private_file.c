/* Darwin-only descriptor experiment. Not linked into any shipping bundle. */
#include <jni.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/acl.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static jfieldID fd_field;

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)reserved;
    JNIEnv *env;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK) return JNI_ERR;
    jclass type = (*env)->FindClass(env, "java/io/FileDescriptor");
    fd_field = type ? (*env)->GetFieldID(env, type, "fd", "I") : NULL;
    return fd_field && !(*env)->ExceptionCheck(env) ? JNI_VERSION_1_6 : JNI_ERR;
}

static void fail(JNIEnv *env, const char *code) {
    jclass type = (*env)->FindClass(env, "java/io/IOException");
    if (type) (*env)->ThrowNew(env, type, code);
}

static int acl_policy(int fd, int parent) {
    acl_t acl;
    do { acl = acl_get_fd_np(fd, ACL_TYPE_EXTENDED); } while (!acl && errno == EINTR);
    if (!acl) return errno == ENOENT;
    acl_entry_t entry;
    errno = 0;
    int result = acl_get_entry(acl, ACL_FIRST_ENTRY, &entry);
    int allowed = 1;
    while (result == 0) {
        acl_flagset_t flags;
        if (!parent || acl_get_flagset_np(entry, &flags) < 0 || acl_get_flag_np(flags, ACL_ENTRY_FILE_INHERIT) != 0) {
            allowed = 0; break;
        }
        errno = 0;
        result = acl_get_entry(acl, ACL_NEXT_ENTRY, &entry);
    }
    if (allowed && !(result == -1 && errno == EINVAL)) allowed = 0;
    acl_free(acl);
    return allowed;
}

static int stat_file(int fd, struct stat *st) {
    int result;
    do { result = fstat(fd, st); } while (result < 0 && errno == EINTR);
    return result;
}

static int stat_filesystem(int fd, struct statfs *fs) {
    int result;
    do { result = fstatfs(fd, fs); } while (result < 0 && errno == EINTR);
    return result;
}

static int private_mode(int fd) {
    int result;
    do { result = fchmod(fd, 0600); } while (result < 0 && errno == EINTR);
    return result;
}

static int get_flags(int fd, int command) {
    int result;
    do { result = fcntl(fd, command); } while (result < 0 && errno == EINTR);
    return result;
}

static int set_flags(int fd, int flags) {
    int result;
    do { result = fcntl(fd, F_SETFL, flags); } while (result < 0 && errno == EINTR);
    return result;
}

static int ordinary_owned_file(int fd, struct stat *st) {
    struct statfs fs;
    return stat_file(fd, st) == 0 && S_ISREG(st->st_mode)
        && st->st_uid == geteuid() && st->st_nlink == 1
        && stat_filesystem(fd, &fs) == 0 && !(fs.f_flags & MNT_IGNORE_OWNERSHIP)
        && acl_policy(fd, 0);
}

JNIEXPORT void JNICALL Java_privatefixture_PrivatePreferenceFile_open0
    (JNIEnv *env, jclass unused, jbyteArray bytes, jobject descriptor) {
    (void)unused;
    if (!bytes || !descriptor || !fd_field) { fail(env, "private-path"); return; }
    if ((*env)->GetIntField(env, descriptor, fd_field) != -1) { fail(env, "private-descriptor-state"); return; }
    jsize length = (*env)->GetArrayLength(env, bytes);
    if (length <= 0 || length >= 1048576) { fail(env, "private-path"); return; }
    char *path = malloc((size_t)length + 1);
    if (!path) { fail(env, "private-allocation"); return; }
    (*env)->GetByteArrayRegion(env, bytes, 0, length, (jbyte *)path);
    if ((*env)->ExceptionCheck(env)) { free(path); return; }
    if (memchr(path, 0, (size_t)length)) { free(path); fail(env, "private-path"); return; }
    path[length] = 0;
    char *base = strrchr(path, '/');
    const char *parent;
    if (base) { *base = 0; base++; parent = path[0] ? path : "/"; }
    else { base = path; parent = "."; }
    if (!base[0] || !strcmp(base, ".") || !strcmp(base, "..")) { free(path); fail(env, "private-path"); return; }
    int dirfd;
    do { dirfd = open(parent, O_RDONLY | O_DIRECTORY | O_CLOEXEC); } while (dirfd < 0 && errno == EINTR);
    if (dirfd < 0) { free(path); fail(env, "private-open"); return; }
    if (!acl_policy(dirfd, 1)) { close(dirfd); free(path); fail(env, "private-parent-policy"); return; }
    int fd;
    do { fd = openat(dirfd, base, O_WRONLY | O_CREAT | O_NOFOLLOW | O_NONBLOCK | O_CLOEXEC, 0600); }
    while (fd < 0 && errno == EINTR);
    close(dirfd); free(path);
    if (fd < 0) { fail(env, "private-open"); return; }
    struct stat st;
    const char *error = NULL;
    if (!ordinary_owned_file(fd, &st)) error = "private-file-policy";
    if (!error && (private_mode(fd) < 0 || !ordinary_owned_file(fd, &st) || (st.st_mode & 07777) != 0600)) error = "private-file-mode";
    int flags = error ? -1 : get_flags(fd, F_GETFL);
    if (!error && (flags < 0 || set_flags(fd, flags & ~O_NONBLOCK) < 0 || (get_flags(fd, F_GETFL) & O_NONBLOCK))) error = "private-file-flags";
    if (!error) {
        int result;
        do { result = ftruncate(fd, 0); } while (result < 0 && errno == EINTR);
        if (result < 0) error = "private-truncate";
    }
    if (error) { close(fd); fail(env, error); return; }
    /* Already attached Java stream becomes the sole owner, as the final action. */
    (*env)->SetIntField(env, descriptor, fd_field, fd);
}

/* Test-only metadata observation; never grants or shares ownership of the fd. */
JNIEXPORT jint JNICALL Java_privatefixture_PrivatePreferenceFile_flags0
    (JNIEnv *env, jclass unused, jobject descriptor) {
    (void)unused;
    int fd = (*env)->GetIntField(env, descriptor, fd_field);
    int descriptor_flags = get_flags(fd, F_GETFD), status_flags = get_flags(fd, F_GETFL);
    if (descriptor_flags < 0 || status_flags < 0) { fail(env, "private-file-flags"); return -1; }
    return ((descriptor_flags & FD_CLOEXEC) ? 1 : 0) | ((status_flags & O_NONBLOCK) ? 2 : 0);
}
