/* Stale ABI fixture: all lazy symbols bind, all invalid-argument codes match,
 * but the version is wrong. None of these methods can create a file. */
#include <jni.h>
static void reject(JNIEnv *env, const char *code) {
    jclass type = (*env)->FindClass(env, "java/io/IOException");
    if (!type || (*env)->ExceptionCheck(env)) return;
    (*env)->ThrowNew(env, type, code); (*env)->DeleteLocalRef(env, type);
}
JNIEXPORT void JNICALL Java_atomicfixture_AtomicPreferenceFile_abort0(JNIEnv *env, jclass unused, jlong handle) {
    (void)unused; (void)handle; reject(env, "atomic-session-consumed");
}
JNIEXPORT void JNICALL Java_atomicfixture_AtomicPreferenceFile_commit0(JNIEnv *env, jclass unused, jlong handle) {
    (void)unused; (void)handle; reject(env, "atomic-session-consumed");
}
JNIEXPORT void JNICALL Java_atomicfixture_AtomicPreferenceFile_begin0(JNIEnv *env, jclass unused, jbyteArray bytes, jobject descriptor, jobject owner) {
    (void)unused; (void)bytes; (void)descriptor; (void)owner; reject(env, "atomic-session-state");
}
JNIEXPORT jint JNICALL Java_atomicfixture_AtomicPreferenceFile_version0(JNIEnv *env, jclass unused) {
    (void)env; (void)unused; return 0;
}
