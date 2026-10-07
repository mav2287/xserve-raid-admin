"""Verifier-valid negative controls for the memory-only socket setup gate."""
import hashlib,re,subprocess
from pathlib import Path
from audit_support import JAVA_FLAGS,isolated_env,run_jdk
from class_patch import ClassFile,word
from worker_exit_patch import Pool
from sync_ownership_patch import compose,method_code,code_attribute
from baseline import write_jar
changes={
 'attached-cause':('return clean;','clean.initCause(error); return clean;'),
 'ignored-timeout-error':('socket.setSoTimeout(readTimeout);','try { socket.setSoTimeout(readTimeout); } catch (SocketException ignored) { }'),
 'missing-close':('if (!ready) {','if (false) {'),
 'lost-connect-category':('clean = new ConnectException(MESSAGE);','clean = new IOException(MESSAGE);'),
 'wrapped-security':('throw denied;','throw new IOException(MESSAGE);'),
 'escaped-runtime':('} catch (RuntimeException invalid) {\n            throw new IOException(MESSAGE);',''),
 'lost-setup-category': ('} catch (IOException failure) {\n            throw fixed(failure);\n        } catch (RuntimeException', '} catch (IOException failure) {\n            throw new IOException(MESSAGE);\n        } catch (RuntimeException'),
 'narrow-close-catch': ('catch (Throwable ignored)', 'catch (IOException ignored)'),
 'wrapped-error':('} finally {','} catch (Error fatal) { throw new IOException(MESSAGE); } finally {'),
}
expected_assertions={name:'Configuration assertion' for name in changes}
expected_assertions.update({'ignored-timeout-error':'Setup failure ignored','lost-connect-category':'Publication assertion','constant-read-timeout':'Publication assertion','wrong-read-field':'Publication assertion','publish-before-configuration':'Publication assertion'})
expected_frames={'attached-cause': ['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)', 'compat.ConfigurationObservation.fixed(ConfigurationObservation.java:38)', 'compat.ConfigurationObservation.main(ConfigurationObservation.java:50)'], 'ignored-timeout-error': ['compat.ConfigurationObservation.main(ConfigurationObservation.java:49)'], 'missing-close': ['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)', 'compat.ConfigurationObservation.main(ConfigurationObservation.java:52)'], 'lost-connect-category': ['ConfigurationPublicationObservation.check(ConfigurationPublicationObservation.java:18)', 'ConfigurationPublicationObservation.main(ConfigurationPublicationObservation.java:115)'], 'wrapped-security': ['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)', 'compat.ConfigurationObservation.main(ConfigurationObservation.java:66)'], 'escaped-runtime': ['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)', 'compat.ConfigurationObservation.main(ConfigurationObservation.java:67)'], 'lost-setup-category': ('} catch (IOException failure) {\n            throw fixed(failure);\n        } catch (RuntimeException', '} catch (IOException failure) {\n            throw new IOException(MESSAGE);\n        } catch (RuntimeException'),
 'narrow-close-catch': ('catch (Throwable ignored)', 'catch (IOException ignored)'),
 'wrapped-error': ['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)', 'compat.ConfigurationObservation.main(ConfigurationObservation.java:66)'], 'constant-read-timeout': ['ConfigurationPublicationObservation.check(ConfigurationPublicationObservation.java:18)', 'ConfigurationPublicationObservation.main(ConfigurationPublicationObservation.java:93)'], 'wrong-read-field': ['ConfigurationPublicationObservation.check(ConfigurationPublicationObservation.java:18)', 'ConfigurationPublicationObservation.main(ConfigurationPublicationObservation.java:102)'], 'publish-before-configuration': ['ConfigurationPublicationObservation.check(ConfigurationPublicationObservation.java:18)', 'ConfigurationPublicationObservation.unpublished(ConfigurationPublicationObservation.java:20)', 'ConfigurationPublicationObservation$MemoryImpl.connect(ConfigurationPublicationObservation.java:32)']}

expected_frames['lost-setup-category']=['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)','compat.ConfigurationObservation.main(ConfigurationObservation.java:50)']
expected_frames['narrow-close-catch']=['compat.ConfigurationObservation.check(ConfigurationObservation.java:9)','compat.ConfigurationObservation.main(ConfigurationObservation.java:74)']

def observe(jdk,runtimes,base,source,classes,probe_hashes,directory):
    rows=[]
    def rejected(name,entries,kind):
        mutant_dir=directory/name;mutant_dir.mkdir(parents=True,exist_ok=True)
        jar=mutant_dir/'mutant.jar';write_jar(jar,entries)
        product={n:hashlib.sha256(v).hexdigest() for n,v in entries.items()
                 if n.endswith('.class') and (n.startswith('compat/') or n=='com/apple/xsr/net/HttpConnection.class')}
        identity=[n[:-6].replace('/','.')+'\t'+str(location)+'\t'+h
            for mapping,location in ((probe_hashes,classes),(product,jar)) for n,h in sorted(mapping.items())]
        idfile=mutant_dir/'identity.tsv';idfile.write_text('\n'.join(identity)+'\n')
        for arch,root in runtimes.items():
            flags=['-Xint','-Xverify:all','-Djava.awt.headless=true','-Duser.home='+str(directory),
                '-Dfixture.identitymanifest='+str(idfile),'-cp',str(jar)+':'+str(classes),'ConfigurationRunner',kind]
            result=subprocess.run([str(root/'Contents/Home/bin/java')]+JAVA_FLAGS+flags,
                env=isolated_env(),capture_output=True,timeout=30)
            first=re.search(rb'^Exception in thread "main" java.lang.AssertionError: (.*)$',result.stderr,re.M)
            actual_frames=re.findall(rb'^\s+at ((?:compat\.ConfigurationObservation|ConfigurationPublicationObservation).*?)$',result.stderr,re.M)
            frames=[f.decode() for f in actual_frames[:len(expected_frames[name])]]
            if result.returncode==0 or result.stdout or first is None or first[1].decode()!=expected_assertions[name] or frames!=expected_frames[name] or b'VerifyError' in result.stderr:
                raise ValueError('Mutant did not fail at its exact intended fixture assertion; raw output withheld')
            rows.append({'mutation':name,'architecture':arch,'execution_mode':'-Xint',
                'mutant_jar_sha256':hashlib.sha256(jar.read_bytes()).hexdigest(),
                'class_identity_manifest_sha256':hashlib.sha256(idfile.read_bytes()).hexdigest(),
                'fixture':kind,'assertion':first[1].decode(),'expected_failing_frames':expected_frames[name],
                'stderr_sha256':hashlib.sha256(result.stderr).hexdigest(),
                'rejected_by_fixture_assertion':True,'verifier_or_timeout_failure':False})
    for name,(before,after) in changes.items():
        if source.count(before)!=1:raise ValueError('Mutant source seam differs')
        folder=directory/name;file=folder/'compat/SocketConfiguration.java';file.parent.mkdir(parents=True)
        file.write_text(source.replace(before,after));compiled=folder/'classes';compiled.mkdir()
        run_jdk(jdk,'javac',['-source','8','-target','8','-d',str(compiled),str(file)],require_empty_stderr=True)
        entries=dict(base);entries['compat/SocketConfiguration.class']=(compiled/'compat/SocketConfiguration.class').read_bytes()
        rejected(name,entries,'publication' if name=='lost-connect-category' else 'direct')
    data=base['com/apple/xsr/net/HttpConnection.class'];cls=ClassFile(data);b,e=method_code(cls,'createSocket','(I)V');code=data[b+14:b+30]
    if code.count(bytes.fromhex('2ab40009'))!=1:raise ValueError('Mutant timeout operand seam differs')
    for name,replacement in (('constant-read-timeout',bytes.fromhex('00117530')),('wrong-read-field',bytes.fromhex('2ab40008'))):
        changed=code.replace(bytes.fromhex('2ab40009'),replacement)
        patched=compose(data,cls,[(b,e,code_attribute(data[b:e],word(3)+word(2),changed,word(0)+word(0)))],cls.pool_count)
        entries=dict(base);entries['com/apple/xsr/net/HttpConnection.class']=patched;rejected(name,entries,'publication')
    pool=Pool(cls);constructor=pool.member(10,49,'<init>','()V')
    early=bytes.fromhex('2abb003159b7')+word(constructor)+bytes.fromhex('b5001a')
    patched=compose(data,cls,[(b,e,code_attribute(data[b:e],word(3)+word(2),early+code,word(0)+word(0)))],pool.n,bytes(pool.extra))
    entries=dict(base);entries['com/apple/xsr/net/HttpConnection.class']=patched;rejected('publish-before-configuration',entries,'publication')
    if len(rows)!=24 or {(r['mutation'],r['architecture']) for r in rows}!={(m,a) for m in expected_frames for a in ('aarch64','x64')}:
        raise ValueError('Complete twelve-mutant, two-runtime matrix required')
    return rows
