/* Nonshipping Darwin transaction experiment. No controller or Keychain APIs. */
#include <jni.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/acl.h>
#include <sys/stdio.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

typedef struct {
    int dirfd, verify_fd;
    char *base;
    char temporary[43];
    int created, target_present;
    dev_t temporary_device, target_device;
    ino_t temporary_inode, target_inode;
} Session;

static jfieldID descriptor_field, handle_field;
static jclass io_exception, open_exception;

/* Eager binding ensures a mismatched library cannot fail after begin has created a file. */
static jint version_native(JNIEnv *, jclass);
static void begin_native(JNIEnv *, jclass, jbyteArray, jobject, jobject);
static void commit_native(JNIEnv *, jclass, jlong);
static void abort_native(JNIEnv *, jclass, jlong);

static void clear_globals(JNIEnv *env) {
    if (io_exception) (*env)->DeleteGlobalRef(env, io_exception);
    if (open_exception) (*env)->DeleteGlobalRef(env, open_exception);
    io_exception = open_exception = NULL;
    descriptor_field = handle_field = NULL;
}

JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM *vm, void *reserved) {
    (void)reserved;
    JNIEnv *env;
    jclass fd = NULL, session = NULL, io = NULL, open = NULL, helper = NULL;
    int registration_attempted = 0;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) != JNI_OK) return JNI_ERR;
    fd = (*env)->FindClass(env, "java/io/FileDescriptor");
    if (!fd || (*env)->ExceptionCheck(env)) goto failed;
    session = (*env)->FindClass(env, "atomicfixture/AtomicPreferenceFile$Session");
    if (!session || (*env)->ExceptionCheck(env)) goto failed;
    io = (*env)->FindClass(env, "java/io/IOException");
    if (!io || (*env)->ExceptionCheck(env)) goto failed;
    open = (*env)->FindClass(env, "java/io/FileNotFoundException");
    if (!open || (*env)->ExceptionCheck(env)) goto failed;
    helper = (*env)->FindClass(env, "atomicfixture/AtomicPreferenceFile");
    if (!helper || (*env)->ExceptionCheck(env)) goto failed;
    descriptor_field = (*env)->GetFieldID(env, fd, "fd", "I");
    if (!descriptor_field || (*env)->ExceptionCheck(env)) goto failed;
    handle_field = (*env)->GetFieldID(env, session, "handle", "J");
    if (!handle_field || (*env)->ExceptionCheck(env)) goto failed;
    io_exception = (*env)->NewGlobalRef(env, io);
    if (!io_exception || (*env)->ExceptionCheck(env)) goto failed;
    open_exception = (*env)->NewGlobalRef(env, open);
    if (!open_exception || (*env)->ExceptionCheck(env)) goto failed;
    JNINativeMethod methods[] = {
        {"version0", "()I", (void *)version_native},
        {"begin0", "([BLjava/io/FileDescriptor;Latomicfixture/AtomicPreferenceFile$Session;)V", (void *)begin_native},
        {"commit0", "(J)V", (void *)commit_native},
        {"abort0", "(J)V", (void *)abort_native}
    };
    registration_attempted = 1;
    if ((*env)->RegisterNatives(env, helper, methods, 4) != JNI_OK || (*env)->ExceptionCheck(env)) goto failed;
    (*env)->DeleteLocalRef(env, fd); (*env)->DeleteLocalRef(env, session);
    (*env)->DeleteLocalRef(env, io); (*env)->DeleteLocalRef(env, open); (*env)->DeleteLocalRef(env, helper);
    return JNI_VERSION_1_6;
failed:
    /* RegisterNatives may bind a prefix before failure. Remove that prefix
     * before unload, preserving the original lookup/registration exception. */
    if (registration_attempted) {
        jthrowable pending = (*env)->ExceptionOccurred(env);
        if (pending) (*env)->ExceptionClear(env);
        (*env)->UnregisterNatives(env, helper);
        if ((*env)->ExceptionCheck(env)) (*env)->ExceptionClear(env);
        if (pending) { (*env)->Throw(env, pending); (*env)->DeleteLocalRef(env, pending); }
    }
    /* Ref deletion is legal with a pending exception. No further lookup is attempted. */
    clear_globals(env);
    if (fd) (*env)->DeleteLocalRef(env, fd);
    if (session) (*env)->DeleteLocalRef(env, session);
    if (io) (*env)->DeleteLocalRef(env, io);
    if (open) (*env)->DeleteLocalRef(env, open);
    if (helper) (*env)->DeleteLocalRef(env, helper);
    return JNI_ERR;
}

JNIEXPORT void JNICALL JNI_OnUnload(JavaVM *vm, void *reserved) {
    (void)reserved;
    JNIEnv *env;
    if ((*vm)->GetEnv(vm, (void **)&env, JNI_VERSION_1_6) == JNI_OK) clear_globals(env);
}

/* Bump whenever the transaction contract changes. Library hashes remain required. */
static jint version_native(JNIEnv *env, jclass unused) {
    (void)env; (void)unused;
    return 0x58415201;
}

static void fail(JNIEnv *env, const char *code, int opening) {
    (*env)->ThrowNew(env, opening ? open_exception : io_exception, code);
}

static int stat_fd(int fd, struct stat *st) {
    int value;
    do { value = fstat(fd, st); } while (value < 0 && errno == EINTR);
    return value;
}

static int stat_name(int fd, const char *name, struct stat *st) {
    int value;
    do { value = fstatat(fd, name, st, AT_SYMLINK_NOFOLLOW); } while (value < 0 && errno == EINTR);
    return value;
}

static int acl_ok(int fd, int parent) {
    acl_t acl;
    do { acl = acl_get_fd_np(fd, ACL_TYPE_EXTENDED); } while (!acl && errno == EINTR);
    if (!acl) return errno == ENOENT;
    acl_entry_t entry;
    errno = 0;
    int value = acl_get_entry(acl, ACL_FIRST_ENTRY, &entry), allowed = 1;
    while (value == 0) {
        acl_flagset_t flags;
        acl_tag_t tag;
        if (!parent || acl_get_flagset_np(entry, &flags) < 0 || acl_get_flag_np(flags, ACL_ENTRY_FILE_INHERIT) != 0
            || acl_get_tag_type(entry, &tag) < 0 || tag == ACL_EXTENDED_ALLOW) { allowed = 0; break; }
        errno = 0;
        value = acl_get_entry(acl, ACL_NEXT_ENTRY, &entry);
    }
    if (allowed && !(value == -1 && errno == EINVAL)) allowed = 0;
    acl_free(acl);
    return allowed;
}

static int owner_filesystem(int fd) {
    struct statfs fs;
    int value;
    do { value = fstatfs(fd, &fs); } while (value < 0 && errno == EINTR);
    return value == 0 && !(fs.f_flags & MNT_IGNORE_OWNERSHIP);
}

static int parent_ok(int fd) {
    struct stat st;
    return stat_fd(fd, &st) == 0 && S_ISDIR(st.st_mode) && (st.st_uid == geteuid() || st.st_uid == 0)
        && !(st.st_mode & 0022) && owner_filesystem(fd) && acl_ok(fd, 1);
}

static int target_ok(const struct stat *st) {
    return S_ISREG(st->st_mode) && st->st_uid == geteuid()
        && !(st->st_flags & (UF_IMMUTABLE | UF_APPEND | SF_IMMUTABLE | SF_APPEND));
}

/* Permission preflight preserves legacy read-only/deny-write intent. It is not
 * an atomic authorization check; same-uid/root races remain outside the threat model. */
static int target_writable(Session *s) {
    int value;
    do { value = faccessat(s->dirfd, s->base, W_OK, AT_EACCESS | AT_SYMLINK_NOFOLLOW); } while (value < 0 && errno == EINTR);
    return value == 0;
}

static int temporary_ok(Session *s) {
    struct stat st, parent;
    return stat_fd(s->dirfd, &parent) == 0 && stat_fd(s->verify_fd, &st) == 0 && S_ISREG(st.st_mode) && st.st_uid == geteuid()
        && st.st_dev == parent.st_dev && st.st_dev == s->temporary_device && st.st_ino == s->temporary_inode && st.st_nlink == 1
        && (st.st_mode & 07777) == 0600 && owner_filesystem(s->verify_fd) && acl_ok(s->verify_fd, 0);
}

/* Verify the recorded inode before unlink; same-uid/root check-to-unlink races
 * remain outside the threat model. Never intentionally unlink a substituted name. */
static int remove_temporary(Session *s) {
    if (!s->created) return 1;
    struct stat st;
    if (stat_name(s->dirfd, s->temporary, &st) < 0) return errno == ENOENT;
    if (!S_ISREG(st.st_mode) || st.st_uid != geteuid() || st.st_dev != s->temporary_device || st.st_ino != s->temporary_inode) return 0;
    int value;
    do { value = unlinkat(s->dirfd, s->temporary, 0); } while (value < 0 && errno == EINTR);
    return value == 0;
}

static void fail_cleanup(JNIEnv *env, const char *code, int opening, int issues) {
    char combined[96];
    if (!issues) { fail(env, code, opening); return; }
    snprintf(combined, sizeof(combined), "%s%s%s", code, issues & 1 ? "+leftover" : "", issues & 2 ? "+close" : "");
    fail(env, combined, opening);
}

static int consume(Session *s, int aborting) {
    int issues = aborting && !remove_temporary(s) ? 1 : 0;
    /* No retries on close: an EINTR retry could affect a reused descriptor. */
    if (s->verify_fd >= 0 && close(s->verify_fd) < 0) issues |= 2;
    if (s->dirfd >= 0 && close(s->dirfd) < 0) issues |= 2;
    free(s->base); free(s);
    return issues;
}

static void begin_native
    (JNIEnv *env, jclass unused, jbyteArray bytes, jobject descriptor, jobject owner) {
    (void)unused;
    if (!bytes || !descriptor || !owner || (*env)->GetIntField(env, descriptor, descriptor_field) != -1
        || (*env)->GetLongField(env, owner, handle_field) != 0) { fail(env, "atomic-session-state", 0); return; }
    jsize length = (*env)->GetArrayLength(env, bytes);
    if (length <= 0 || length >= 1048576) { fail(env, "atomic-path", 1); return; }
    char *path = malloc((size_t)length + 1);
    Session *s = calloc(1, sizeof(*s));
    if (!path || !s) { free(path); free(s); fail(env, "atomic-allocation", 0); return; }
    s->dirfd = s->verify_fd = -1;
    (*env)->GetByteArrayRegion(env, bytes, 0, length, (jbyte *)path);
    if ((*env)->ExceptionCheck(env)) { free(path); consume(s, 0); return; }
    if (memchr(path, 0, (size_t)length)) { free(path); int cleaned = consume(s, 0); fail_cleanup(env, "atomic-path", 1, cleaned); return; }
    path[length] = 0;
    char *base = strrchr(path, '/'); const char *parent;
    if (base) { *base = 0; base++; parent = path[0] ? path : "/"; }
    else { base = path; parent = "."; }
    if (!base[0] || !strcmp(base, ".") || !strcmp(base, "..")) { free(path); int cleaned = consume(s, 0); fail_cleanup(env, "atomic-path", 1, cleaned); return; }
    s->base = strdup(base);
    if (!s->base) { free(path); int cleaned = consume(s, 0); fail_cleanup(env, "atomic-allocation", 0, cleaned); return; }
    do { s->dirfd = open(parent, O_RDONLY | O_DIRECTORY | O_CLOEXEC); } while (s->dirfd < 0 && errno == EINTR);
    free(path);
    if (s->dirfd < 0) { int cleaned = consume(s, 0); fail_cleanup(env, "atomic-parent-open", 1, cleaned); return; }
    if (!parent_ok(s->dirfd)) { int cleaned = consume(s, 0); fail_cleanup(env, "atomic-parent-policy", 0, cleaned); return; }
    struct stat target;
    if (stat_name(s->dirfd, s->base, &target) == 0) {
        if (!target_ok(&target)) { int cleaned = consume(s, 0); fail_cleanup(env, "atomic-target-policy", 0, cleaned); return; }
        if (!target_writable(s)) { int cleaned = consume(s, 0); fail_cleanup(env, "atomic-target-unwritable", 0, cleaned); return; }
        s->target_present = 1; s->target_device = target.st_dev; s->target_inode = target.st_ino;
    } else if (errno != ENOENT) { int cleaned = consume(s, 0); fail_cleanup(env, "atomic-target-stat", 0, cleaned); return; }
    int fd = -1;
    for (int attempt = 0; attempt < 4; attempt++) {
        unsigned char random[16]; static const char hex[] = "0123456789abcdef";
        arc4random_buf(random, sizeof(random)); memcpy(s->temporary, ".xra-", 5);
        for (int i = 0; i < 16; i++) { s->temporary[5 + 2*i] = hex[random[i] >> 4]; s->temporary[6 + 2*i] = hex[random[i] & 15]; }
        memcpy(s->temporary + 37, ".tmp", 5);
        /* Do not blindly retry create on EINTR: a remote server may have created
         * the name already. A private leftover is safer than unlinking an unknown inode. */
        fd = openat(s->dirfd, s->temporary, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
        if (fd >= 0 || errno != EEXIST) break;
    }
    if (fd < 0) {
        int interrupted = errno == EINTR;
        int cleaned = consume(s, 0); fail_cleanup(env, interrupted ? "atomic-temporary-create-uncertain" : "atomic-temporary-open", 1, cleaned); return;
    }
    struct stat temporary;
    /* Only descriptor metadata establishes identity. A name-only fallback could
     * select a substituted inode. If both attempts fail, explicitly report the
     * possible private empty leftover rather than unlink an unverified name. */
    if (stat_fd(fd, &temporary) < 0 && stat_fd(fd, &temporary) < 0) {
        int raw_issue = close(fd) < 0 ? 2 : 0; int cleaned = consume(s, 0) | raw_issue; fail_cleanup(env, "atomic-temporary-stat-leftover", 0, cleaned); return;
    }
    s->created = 1; s->temporary_device = temporary.st_dev; s->temporary_inode = temporary.st_ino;
    int mode;
    do { mode = fchmod(fd, 0600); } while (mode < 0 && errno == EINTR);
    if (mode < 0) { int raw_issue = close(fd) < 0 ? 2 : 0; int cleaned = consume(s, 1) | raw_issue; fail_cleanup(env, "atomic-temporary-mode", 0, cleaned); return; }
    do { s->verify_fd = fcntl(fd, F_DUPFD_CLOEXEC, 0); } while (s->verify_fd < 0 && errno == EINTR);
    if (s->verify_fd < 0 || !temporary_ok(s)) {
        const char *code = s->verify_fd < 0 ? "atomic-temporary-dup" : "atomic-temporary-policy";
        int raw_issue = close(fd) < 0 ? 2 : 0;
        int cleaned = consume(s, 1) | raw_issue; fail_cleanup(env, code, 0, cleaned); return;
    }
    /* These two valid-field stores cannot fail. Do not insert fallible JNI work
     * between them; the Java owner must be able to abort once fd is published. */
    (*env)->SetLongField(env, owner, handle_field, (jlong)(intptr_t)s);
    (*env)->SetIntField(env, descriptor, descriptor_field, fd);
}

static void abort_native
    (JNIEnv *env, jclass unused, jlong handle) {
    (void)unused;
    if (!handle) { fail(env, "atomic-session-consumed", 0); return; }
    int issues = consume((Session *)(intptr_t)handle, 1);
    if (issues) fail_cleanup(env, "atomic-abort", 0, issues);
}

static void commit_native
    (JNIEnv *env, jclass unused, jlong handle) {
    (void)unused;
    if (!handle) { fail(env, "atomic-session-consumed", 0); return; }
    Session *s = (Session *)(intptr_t)handle;
    const char *error = NULL; struct stat temporary, target;
    if (!temporary_ok(s) || stat_name(s->dirfd, s->temporary, &temporary) < 0
        || temporary.st_dev != s->temporary_device || temporary.st_ino != s->temporary_inode) error = "atomic-temporary-changed";
    int target_exists = error ? -1 : stat_name(s->dirfd, s->base, &target);
    if (!error && ((s->target_present && (target_exists < 0 || !target_ok(&target) || target.st_dev != s->target_device || target.st_ino != s->target_inode))
        || (!s->target_present && (target_exists == 0 || errno != ENOENT)))) error = "atomic-target-changed";
    if (!error && s->target_present && !target_writable(s)) error = "atomic-target-unwritable-at-commit";
    if (!error && !parent_ok(s->dirfd)) error = "atomic-parent-changed";
    if (!error) {
        struct statfs fs; int value;
        do { value = fstatfs(s->verify_fd, &fs); } while (value < 0 && errno == EINTR);
        if (value < 0) error = "atomic-temporary-filesystem";
        else if (!(fs.f_flags & MNT_LOCAL)) {
            /* The dup keeps the open description alive after Java close. Check
             * remote writeback before replacing the original; not power-loss durability. */
            do { value = fsync(s->verify_fd); } while (value < 0 && errno == EINTR);
            if (value < 0) error = "atomic-temporary-sync";
        }
    }
    if (!error) {
        int value;
        do { value = s->target_present ? renameat(s->dirfd, s->temporary, s->dirfd, s->base)
            : renameatx_np(s->dirfd, s->temporary, s->dirfd, s->base, RENAME_EXCL); } while (value < 0 && errno == EINTR);
        if (value < 0) error = "atomic-rename";
    }
    int closed = consume(s, error != NULL);
    if (error) fail_cleanup(env, error, 0, closed);
    else if (closed) fail(env, "atomic-committed:close", 0);
}
