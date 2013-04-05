# -*- coding: utf-8 -*-

#===============================================================================
# Created on Nov 30, 2012
# 
# @author: bneron
# @contact: user_email
# @organization: organization_name
# @license: license
#===============================================================================


import sys
import os

TXSSCAN_HOME = os.path.abspath('..')
if not TXSSCAN_HOME in sys.path: 
    sys.path.append(os.path.abspath('..') )

import unittest
import shutil
from txsscanlib.config import Config
from txsscanlib.database import Database, SequenceInfo

 
class Test(unittest.TestCase):

    _data_dir = "./datatest/res_search" 
    
    def __init__(self,methodName='runTest'):
        super(Test, self).__init__(methodName)
        def fake_init(obj, cfg):
            obj.cfg = cfg
            obj._fasta_path = cfg.sequence_db
            obj.name = os.path.basename(cfg.sequence_db)
        self.fake_init = fake_init
        self.real_init = Database.__init__
    
    def setUp(self):
        
        self.cfg = Config( hmmer_exe = "hmmsearch",
                           sequence_db = "./datatest/prru_psae.001.c01.fasta",
                           db_type = "gembase",
                           e_value_res = 1,
                           i_evalue_sel = 0.5,
                           def_dir = "../data/DEF",
                           res_search_dir = '/tmp',
                           res_search_suffix = ".search_hmm.out",
                           profile_dir = "../data/profiles",
                           profile_suffix = ".fasta-aln_edit.hmm",
                           res_extract_suffix = "",
                           log_level = 30,
                           log_file = '/dev/null'
                           )

        shutil.copy(self.cfg.sequence_db, self.cfg.working_dir)
        self.cfg.options['sequence_db'] = os.path.join( self.cfg.working_dir, os.path.basename(self.cfg.sequence_db))


    def tearDown(self):
        try:
            shutil.rmtree(self.cfg.working_dir)
        except:
            pass

    def test_find_hmmer_indexes_no_files(self):
        db = Database(self.cfg)
        #tester pas de fichier
        hmmer_idx = db._find_hmmer_indexes()
        self.assertListEqual(hmmer_idx, [])

    def test_find_hmmer_indexes_all_files(self):
        db = Database(self.cfg)
        #tester tous les fichiers
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        files_2_find = []
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
            files_2_find.append(new_idx)
        hmmer_idx = db._find_hmmer_indexes()
        self.assertListEqual(hmmer_idx, files_2_find)


    def test_find_hmmer_indexes_all_files_and_pal(self):
        db = Database(self.cfg)
        #tester tous les fichiers + pal
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq', '.pal')
        files_2_find = []
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
        self.assertRaises(RuntimeError, db._find_hmmer_indexes)


    def test_find_hmmer_indexes_some_files(self):
        db = Database(self.cfg)        
        #tester pas tous les fichiers
        suffixes = ('.phr', '.pin', '.psd', '.psi')
        files_2_find = []
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
        self.assertRaises(RuntimeError, db._find_hmmer_indexes)


    def test_find_hmmer_indexes_lack_pal(self):
        db = Database(self.cfg)   
        #tester plusieurs index pas de pal
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        files_2_find = []
        for s in  suffixes:
            for i in range(2):
                new_idx = os.path.join( self.cfg.sequence_db+ str(i) + s)
                open(new_idx, 'w')
        self.assertRaises(RuntimeError, db._find_hmmer_indexes)


    def test_find_hmmer_indexes_all_files_and_2virtual(self):
        db = Database(self.cfg)           
        #tester 1 fichier index + pal    
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq', '.pal')
        files_2_find = []
        for s in  suffixes:
            for i in range(2):
                new_idx = os.path.join( self.cfg.sequence_db+ str(i) + s)
                open(new_idx, 'w')
                files_2_find.append(new_idx)
        self.assertRaises(RuntimeError, db._find_hmmer_indexes)


    def test_find_hmmer_indexes_all_files_and_virtual(self):
        db = Database(self.cfg)           
        #tester index + pal    
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        files_2_find = []
        for s in  suffixes:
            for i in range(2):
                new_idx = os.path.join("%s.%d.%s" %(self.cfg.sequence_db, i, s))
                open(new_idx, 'w')
                files_2_find.append(new_idx)
        new_idx = os.path.join( self.cfg.sequence_db + '.pal')
        open(new_idx, 'w')
        files_2_find.append(new_idx)
        files_2_find.sort()
        hmmer_idx = db._find_hmmer_indexes()
        hmmer_idx.sort()
        self.assertListEqual(hmmer_idx, files_2_find)


    def test_find_my_indexes(self):
        db = Database(self.cfg) 
        self.assertIsNone(db._find_my_indexes())
        new_idx = os.path.join( os.path.dirname(self.cfg.sequence_db), db.name + ".idx")
        open(new_idx, 'w')
        self.assertEqual(db._find_my_indexes(), new_idx)


    def test_build_no_idx(self):
        db = Database(self.cfg)
        db.build()
        my_idx = db._find_my_indexes()
        hmmer_idx = db._find_hmmer_indexes()
        self.assertEqual(my_idx, os.path.join( os.path.dirname(self.cfg.sequence_db), db.name + ".idx"))
        self.assertEqual( hmmer_idx , [ self.cfg.sequence_db + suffix for suffix in ('.phr', '.pin', '.psd', '.psi', '.psq')])


    def test_build_with_idx(self):
        #put fake hmmer indexes
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
        db = Database(self.cfg)
        new_idx = open(os.path.join( os.path.dirname(self.cfg.sequence_db), db.name + ".idx"), 'w')
        db.build()
        my_idx = db._find_my_indexes()
        hmmer_idx = db._find_hmmer_indexes()
        for f in hmmer_idx +[my_idx]:
            self.assertEqual(os.path.getsize(f), 0)


    def test_build_force(self):
        #put fake hmmer indexes
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
        db = Database(self.cfg)
        new_idx = open(os.path.join( os.path.dirname(self.cfg.sequence_db), db.name + ".idx"), 'w')
        db.build(force = True)
        my_idx = db._find_my_indexes()
        hmmer_idx = db._find_hmmer_indexes()
        for f in hmmer_idx +[my_idx]:
            self.assertNotEqual(os.path.getsize(f), 0)
            
    
    def test_build_not_writable(self):
        db = Database(self.cfg)
        idx_dir = os.path.join( os.path.dirname(self.cfg.sequence_db))
        os.chmod(idx_dir, 0000)
        self.assertRaises( IOError, db.build )
        os.chmod(idx_dir, 0777)    

    def test_open(self):
        db = Database(self.cfg)
        self.assertRaises(IOError, db.open)
        db.build()
        db.open()
        self.assertNotEqual(db._my_open_db, None)

    def test_close(self):
        db = Database(self.cfg)
        db.build()
        db.open()
        self.assertNotEqual(db._my_open_db, None)
        db.close()
        self.assertIsNone(db._my_open_db)

    
    def test_get_item(self):
        db = Database(self.cfg)
        #put fake hmmer indexes
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
        #build only new txsscan indexes
        db.build()
        self.assertRaises(IOError, db.__getitem__, 'PRRU001c01_027920')
        with db.open():
            self.assertRaises(KeyError, db.__getitem__ ,'ZZZZZ')
            seq_info_from_db = db['PRRU001c01_027920']
            self.assertEqual(seq_info_from_db, SequenceInfo( 'PRRU001c01_027920', 401, 2730) )


    def test_get(self):
        db = Database(self.cfg)
        #put fake hmmer indexes
        suffixes = ('.phr', '.pin', '.psd', '.psi', '.psq')
        for s in  suffixes:
            new_idx = os.path.join( self.cfg.sequence_db + s)
            open(new_idx, 'w')
        #build only new txsscan indexes
        db.build()
        self.assertRaises(IOError, db.get, 'PRRU001c01_027920')
        with db.open():
            self.assertIsNone(db.get('PRRU001c01_') , None)
            self.assertListEqual(db.get('_027920', [] ) , [] )
            seq_info_from_db = db.get('PRRU001c01_027920')
            self.assertEqual(seq_info_from_db, SequenceInfo( 'PRRU001c01_027920', 401, 2730) )
        

        
if __name__ == "__main__":
    unittest.main()